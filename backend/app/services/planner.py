import math
import json
from datetime import date, timedelta
from itertools import combinations
from typing import Any

from ortools.sat.python import cp_model
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..models import (
    Application,
    CalendarHoliday,
    ConflictRecord,
    EvcPlan,
    EvcPlanAssignment,
    Expert,
    ExpertAvailability,
    Institution,
    Region,
    Notification,
    User,
)
from .audit import append_event
from .workflow import apply_transition


TAG_CATALOG = ("CIVIL", "MECH", "ELEC", "CSE", "MGMT", "ARCH")


def _working_dates(db: Session, count: int = 10) -> list[date]:
    holidays = {row.date for row in db.query(CalendarHoliday).all()}
    cursor = Clock.now().date()
    result: list[date] = []
    while len(result) < count:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5 and cursor not in holidays:
            result.append(cursor)
    return result


def _required_tags(application: Application) -> list[str]:
    reference_index = int(application.reference_no[-4:])
    first = TAG_CATALOG[(reference_index + 1) % len(TAG_CATALOG)]
    if application.application_type == "NEW_PROGRAM_OR_LEVEL":
        second = TAG_CATALOG[(reference_index + 3) % len(TAG_CATALOG)]
        return sorted({first, second})
    return [first]


def _panel_size(application: Application) -> int:
    return 2 + (application.priority % 2)


def _distance_km(regions: dict[str, Region], expert: Expert, application: Application) -> float:
    home = regions.get(expert.home_region)
    destination = regions.get(application.region_code)
    if home is None or destination is None:
        return 0.0
    lat1, lat2 = math.radians(home.latitude), math.radians(destination.latitude)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(destination.longitude - home.longitude)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _metrics(assignments: list[dict[str, Any]], applications: dict[str, Application], experts: list[Expert], regions: dict[str, Region]) -> dict[str, Any]:
    scheduled = [item for item in assignments if item["scheduled"]]
    loads = {expert.id: 0 for expert in experts}
    travel = 0.0
    weighted_age = 0.0
    today = Clock.now().date()
    expert_by_name = {expert.name: expert for expert in experts}
    for item in scheduled:
        application = applications[item["case"]]
        weighted_age += application.priority * max(0, (today - as_utc(application.created_at).date()).days)
        if application.visit_mode == "physical":
            travel += sum(_distance_km(regions, expert_by_name[name], application) for name in item["panel"])
        for name in item["panel"]:
            loads[expert_by_name[name].id] += 1
    values = list(loads.values())
    return {
        "scheduled_count": len(scheduled),
        "priority_weighted_ageing": round(weighted_age, 2),
        "total_travel_km": round(travel, 2),
        "workload_spread": max(values, default=0) - min(values, default=0),
    }


def _first_exclusion_reason(
    expert: Expert,
    application: Application,
    visit_date: date,
    conflicts: set[tuple[int, int]],
    availability: set[tuple[int, date]],
    used_cases_per_expert: dict[int, int],
    assigned_on_day: set[tuple[int, date]],
) -> str | None:
    if (expert.id, application.institution_id) in conflicts:
        return "Conflict of interest"
    if (expert.id, visit_date) not in availability:
        return "Unavailable on visit date"
    required = set(_required_tags(application))
    if not required.intersection(expert.tags.split(",")):
        return "Expertise tag mismatch"
    if used_cases_per_expert.get(expert.id, 0) >= expert.max_visits:
        return "Window workload cap reached"
    if (expert.id, visit_date) in assigned_on_day:
        return "Already booked that day"
    return None


def _greedy_baseline(
    cases: list[Application],
    experts: list[Expert],
    dates: list[date],
    conflicts: set[tuple[int, int]],
    availability: set[tuple[int, date]],
) -> list[dict[str, Any]]:
    scheduled_count: dict[int, int] = {expert.id: 0 for expert in experts}
    assigned_on_day: set[tuple[int, date]] = set()
    assignments: list[dict[str, Any]] = []
    for application in sorted(cases, key=lambda item: (as_utc(item.created_at), item.reference_no)):
        required = set(_required_tags(application))
        panel_size = _panel_size(application)
        proposal = None
        for visit_date in dates:
            candidates = [
                expert for expert in experts
                if (expert.id, application.institution_id) not in conflicts
                and (expert.id, visit_date) in availability
                and (expert.id, visit_date) not in assigned_on_day
                and scheduled_count[expert.id] < expert.max_visits
            ]
            for panel in combinations(candidates, panel_size):
                if not required.issubset({tag for expert in panel for tag in expert.tags.split(",")}):
                    continue
                proposal = (visit_date, panel)
                break
            if proposal:
                break
        if proposal is None:
            assignments.append({"case": application.reference_no, "scheduled": False, "reason": "Greedy baseline found no feasible panel"})
            continue
        visit_date, panel = proposal
        for expert in panel:
            scheduled_count[expert.id] += 1
            assigned_on_day.add((expert.id, visit_date))
        assignments.append({
            "case": application.reference_no,
            "scheduled": True,
            "visit_date": visit_date.isoformat(),
            "panel": [expert.name for expert in panel],
            "visit_mode": application.visit_mode,
            "reason": "Oldest-first baseline; earliest feasible day and first available panel",
        })
    return assignments


def _validate_assignments(
    assignments: list[dict[str, Any]],
    applications: dict[str, Application],
    experts: list[Expert],
    dates: list[date],
    conflicts: set[tuple[int, int]],
    availability: set[tuple[int, date]],
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    experts_by_name = {expert.name: expert for expert in experts}
    visits_per_expert: dict[int, int] = {}
    visits_per_day: dict[tuple[int, str], int] = {}
    seen_cases: set[str] = set()
    valid_dates = {day.isoformat() for day in dates}
    for assignment in assignments:
        if not assignment["scheduled"]:
            continue
        reference = assignment["case"]
        application = applications[reference]
        visit_date = assignment["visit_date"]
        panel = [experts_by_name[name] for name in assignment["panel"] if name in experts_by_name]
        if reference in seen_cases:
            violations.append({"rule": "one_visit_per_case", "case": reference})
        seen_cases.add(reference)
        if visit_date not in valid_dates:
            violations.append({"rule": "visit_inside_window", "case": reference})
        if len(panel) != assignment["panel_size"]:
            violations.append({"rule": "panel_size_met", "case": reference})
        covered_tags = {tag for expert in panel for tag in expert.tags.split(",")}
        if not set(_required_tags(application)).issubset(covered_tags):
            violations.append({"rule": "expertise_covered", "case": reference})
        day = date.fromisoformat(visit_date)
        for expert in panel:
            if (expert.id, application.institution_id) in conflicts:
                violations.append({"rule": "conflict_of_interest", "case": reference, "expert": expert.name})
            if (expert.id, day) not in availability:
                violations.append({"rule": "expert_available", "case": reference, "expert": expert.name})
            visits_per_expert[expert.id] = visits_per_expert.get(expert.id, 0) + 1
            day_key = (expert.id, visit_date)
            visits_per_day[day_key] = visits_per_day.get(day_key, 0) + 1
    for expert in experts:
        if visits_per_expert.get(expert.id, 0) > expert.max_visits:
            violations.append({"rule": "expert_window_cap", "expert": expert.name})
    for (expert_id, day), count in visits_per_day.items():
        if count > 1:
            violations.append({"rule": "one_visit_per_expert_per_day", "expert": experts_by_name[next(e.name for e in experts if e.id == expert_id)].name, "date": day})
    return violations


def create_evc_plan(db: Session, actor: User, request_id: str = "") -> dict[str, Any]:
    case_query = db.query(Application).filter(Application.stage == "EVC")
    if actor.region_code:
        case_query = case_query.filter(Application.region_code == actor.region_code)
    cases = case_query.order_by(Application.created_at.asc(), Application.reference_no).limit(10).all()
    experts = db.query(Expert).order_by(Expert.id).all()
    dates = _working_dates(db)
    conflicts = {(row.expert_id, row.institution_id) for row in db.query(ConflictRecord).all()}
    availability = {
        (row.expert_id, row.available_date)
        for row in db.query(ExpertAvailability).filter(ExpertAvailability.available.is_(True)).all()
    }
    regions = {row.code: row for row in db.query(Region).all()}
    if not cases or not experts:
        return {"assignments": [], "scheduled_count": 0, "violations": [], "solver_status": "NO_DATA", "dates": [day.isoformat() for day in dates]}

    model = cp_model.CpModel()
    case_scheduled: dict[int, Any] = {}
    visit_on_date: dict[tuple[int, int], Any] = {}
    expert_used: dict[tuple[int, int], Any] = {}
    assigned: dict[tuple[int, int, int], Any] = {}
    for case_index, application in enumerate(cases):
        case_scheduled[case_index] = model.NewBoolVar(f"scheduled_{case_index}")
        for date_index, _ in enumerate(dates):
            visit_on_date[(case_index, date_index)] = model.NewBoolVar(f"visit_{case_index}_{date_index}")
            day_assignments = []
            for expert_index, expert in enumerate(experts):
                variable = model.NewBoolVar(f"assigned_{case_index}_{expert_index}_{date_index}")
                assigned[(case_index, expert_index, date_index)] = variable
                day_assignments.append(variable)
                if (expert.id, application.institution_id) in conflicts or (expert.id, dates[date_index]) not in availability:
                    model.Add(variable == 0)
            model.Add(sum(day_assignments) == _panel_size(application) * visit_on_date[(case_index, date_index)])
            for expert_index, expert in enumerate(experts):
                model.Add(assigned[(case_index, expert_index, date_index)] <= visit_on_date[(case_index, date_index)])
        model.Add(sum(visit_on_date[(case_index, date_index)] for date_index in range(len(dates))) == case_scheduled[case_index])
        for expert_index, expert in enumerate(experts):
            expert_used[(case_index, expert_index)] = model.NewBoolVar(f"expert_used_{case_index}_{expert_index}")
            day_variables = [assigned[(case_index, expert_index, date_index)] for date_index in range(len(dates))]
            model.Add(sum(day_variables) == expert_used[(case_index, expert_index)])
        for tag in _required_tags(application):
            matching_experts = [expert_index for expert_index, expert in enumerate(experts) if tag in expert.tags.split(",")]
            if not matching_experts:
                model.Add(case_scheduled[case_index] == 0)
            else:
                model.Add(sum(expert_used[(case_index, expert_index)] for expert_index in matching_experts) >= case_scheduled[case_index])

    for expert_index, expert in enumerate(experts):
        model.Add(sum(expert_used[(case_index, expert_index)] for case_index in range(len(cases))) <= expert.max_visits)
        for date_index in range(len(dates)):
            model.Add(sum(assigned[(case_index, expert_index, date_index)] for case_index in range(len(cases))) <= 1)

    loads = [sum(expert_used[(case_index, expert_index)] for case_index in range(len(cases))) for expert_index in range(len(experts))]
    max_load = model.NewIntVar(0, len(cases), "max_load")
    min_load = model.NewIntVar(0, len(cases), "min_load")
    model.AddMaxEquality(max_load, loads)
    model.AddMinEquality(min_load, loads)
    objective = []
    for case_index, application in enumerate(cases):
        age_days = max(0, (Clock.now().date() - as_utc(application.created_at).date()).days)
        objective.append((100_000 + application.priority * 1_000 + min(age_days, 60) * 10) * case_scheduled[case_index])
        if application.visit_mode == "physical":
            for expert_index, expert in enumerate(experts):
                objective.append(-int(_distance_km(regions, expert, application)) * 10 * expert_used[(case_index, expert_index)])
    objective.append(-100 * (max_load - min_load))
    model.Maximize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.random_seed = 42
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"EVC planner could not find a feasible proposal (solver status {solver.StatusName(status)})")

    planned: list[dict[str, Any]] = []
    used_cases_per_expert: dict[int, int] = {}
    assigned_on_day: set[tuple[int, date]] = set()
    for case_index, application in enumerate(cases):
        if not solver.Value(case_scheduled[case_index]):
            planned.append({
                "case": application.reference_no,
                "scheduled": False,
                "reason": "Panel availability, conflict, expertise or workload constraints bind",
                "required_tags": _required_tags(application),
                "panel_size": _panel_size(application),
            })
            continue
        date_index = next(index for index in range(len(dates)) if solver.Value(visit_on_date[(case_index, index)]))
        visit_date = dates[date_index]
        panel = [
            expert for expert_index, expert in enumerate(experts)
            if solver.Value(assigned[(case_index, expert_index, date_index)])
        ]
        for expert in panel:
            used_cases_per_expert[expert.id] = used_cases_per_expert.get(expert.id, 0) + 1
            assigned_on_day.add((expert.id, visit_date))
        selected_ids = {expert.id for expert in panel}
        excluded = []
        for expert in experts:
            if expert.id in selected_ids:
                continue
            reason = _first_exclusion_reason(expert, application, visit_date, conflicts, availability, used_cases_per_expert, assigned_on_day)
            if reason:
                excluded.append({"expert": expert.name, "reason": reason})
        planned.append({
            "case": application.reference_no,
            "scheduled": True,
            "visit_date": visit_date.isoformat(),
            "panel": [expert.name for expert in panel],
            "visit_mode": application.visit_mode,
            "required_tags": _required_tags(application),
            "panel_size": _panel_size(application),
            "reason": "Expertise covered; experts are available, conflict-free and within workload caps",
            "excluded_experts": excluded,
        })

    baseline = _greedy_baseline(cases, experts, dates, conflicts, availability)
    case_by_ref = {item.reference_no: item for item in cases}
    metrics = _metrics(planned, case_by_ref, experts, regions)
    baseline_metrics = _metrics(baseline, case_by_ref, experts, regions)
    violations = _validate_assignments(planned, case_by_ref, experts, dates, conflicts, availability)
    if violations:
        raise RuntimeError(f"Independent hard-constraint validation failed: {violations[0]}")
    plan_record = EvcPlan(
        window_start=dates[0],
        window_end=dates[-1],
        params_json=json.dumps({"seed": 42, "workers": 1, "time_limit_seconds": 10}, sort_keys=True),
        solver_status=solver.StatusName(status),
        metrics_json=json.dumps(metrics, sort_keys=True),
        baseline_json=json.dumps(baseline_metrics, sort_keys=True),
        created_by=actor.id,
        created_at=Clock.now(),
    )
    db.add(plan_record)
    db.flush()
    for assignment in planned:
        application = case_by_ref[assignment["case"]]
        db.add(EvcPlanAssignment(
            plan_id=plan_record.id,
            application_id=application.id,
            visit_date=date.fromisoformat(assignment["visit_date"]) if assignment.get("visit_date") else None,
            panel_json=json.dumps(assignment.get("panel", [])),
            visit_mode=application.visit_mode,
            explanation_json=json.dumps(assignment, sort_keys=True),
            status="PROPOSED" if assignment["scheduled"] else "UNSCHEDULED",
        ))
    append_event(
        db,
        actor.id,
        "EVC_PLAN_PROPOSED",
        "evc_plan",
        str(plan_record.id),
        after={"scheduled_count": metrics["scheduled_count"], "solver_status": solver.StatusName(status)},
        reason="Deterministic CP-SAT proposal; requires coordinator confirmation",
        request_id=request_id,
    )
    db.commit()
    return {
        "plan_id": plan_record.id,
        "assignments": planned,
        "scheduled_count": metrics["scheduled_count"],
        "violations": violations,
        "solver_status": solver.StatusName(status),
        "optimality_gap": round(abs(solver.BestObjectiveBound() - solver.ObjectiveValue()) / max(1, abs(solver.ObjectiveValue())), 4),
        "metrics": metrics,
        "baseline": baseline_metrics,
        "baseline_assignments": baseline,
        "dates": [day.isoformat() for day in dates],
        "notice": "Synthetic proposal; coordinator confirmation required",
    }


def confirm_evc_plan(db: Session, actor: User, plan_id: int, request_id: str = "") -> dict[str, Any]:
    plan = db.get(EvcPlan, plan_id)
    if plan is None:
        raise ValueError("EVC plan was not found")
    if plan.status == "CONFIRMED":
        count = db.query(EvcPlanAssignment).filter(
            EvcPlanAssignment.plan_id == plan.id,
            EvcPlanAssignment.status == "CONFIRMED",
        ).count()
        return {"plan_id": plan.id, "status": plan.status, "confirmed_count": count}
    if plan.status != "PROPOSED":
        raise ValueError(f"Plan cannot be confirmed from status {plan.status}")

    plan_rows = db.query(EvcPlanAssignment).filter(EvcPlanAssignment.plan_id == plan.id).all()
    cases = [db.get(Application, row.application_id) for row in plan_rows]
    applications = {case.reference_no: case for case in cases if case is not None}
    experts = db.query(Expert).all()
    dates = [
        plan.window_start + timedelta(days=offset)
        for offset in range((plan.window_end - plan.window_start).days + 1)
        if (plan.window_start + timedelta(days=offset)).weekday() < 5
    ]
    conflicts = {(row.expert_id, row.institution_id) for row in db.query(ConflictRecord).all()}
    availability = {
        (row.expert_id, row.available_date)
        for row in db.query(ExpertAvailability).filter(ExpertAvailability.available.is_(True)).all()
    }
    proposed = [json.loads(row.explanation_json) for row in plan_rows]
    violations = _validate_assignments(proposed, applications, experts, dates, conflicts, availability)
    if violations:
        raise ValueError(f"Plan failed revalidation: {violations[0]}")

    confirmed = 0
    for row in plan_rows:
        if row.status != "PROPOSED":
            continue
        application = db.get(Application, row.application_id)
        if application is None or application.stage != "EVC":
            raise ValueError("A planned case is no longer in the EVC stage")
        if actor.region_code and actor.region_code != application.region_code:
            raise ValueError("The plan contains a case outside your region scope")
        apply_transition(
            db,
            application,
            actor,
            "CONFIRM_VISIT",
            application.version,
            None,
            request_id,
            f"evc-plan-{plan.id}-case-{application.id}",
            commit=False,
        )
        row.status = "CONFIRMED"
        confirmed += 1
        institution_user = db.query(User).filter(
            User.role == "INSTITUTION_APPLICANT",
            User.institution_id == application.institution_id,
        ).first()
        if institution_user:
            db.add(Notification(
                recipient_id=institution_user.id,
                entity_type="application",
                entity_id=application.reference_no,
                channel="in_app",
                subject="EVC visit scheduled",
                body=f"A synthetic {application.visit_mode} visit was scheduled for {row.visit_date}.",
                status="SIMULATED",
                created_at=Clock.now(),
            ))
    plan.status = "CONFIRMED"
    append_event(
        db,
        actor.id,
        "EVC_PLAN_CONFIRMED",
        "evc_plan",
        str(plan.id),
        before={"status": "PROPOSED"},
        after={"status": "CONFIRMED", "confirmed_count": confirmed},
        request_id=request_id,
    )
    db.commit()
    return {"plan_id": plan.id, "status": plan.status, "confirmed_count": confirmed}
