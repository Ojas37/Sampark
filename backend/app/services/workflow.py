import json
from datetime import date, datetime, timedelta, time
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..models import AppConfig, Application, IdempotencyRecord, InstitutionResponse, Observation, SlaSegment, User
from .audit import append_event


WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = {
    "ONLY_SCRUTINY": {"version": 1, "start": "SCRUTINY", "stages": ["SCRUTINY", "DONE"], "sla_hours": {"SCRUTINY": 120}},
    "SCRUTINY_EVC": {"version": 1, "start": "SCRUTINY", "stages": ["SCRUTINY", "EVC", "DONE"], "sla_hours": {"SCRUTINY": 120, "EVC": 240}},
    "EVC_SHC": {"version": 1, "start": "EVC", "stages": ["EVC", "SHC", "DONE"], "sla_hours": {"EVC": 240, "SHC": 120}},
    "ONLY_EVC": {"version": 1, "start": "EVC", "stages": ["EVC", "DONE"], "sla_hours": {"EVC": 240}},
}


def business_seconds(start: datetime, end: datetime, holidays: frozenset[date] = frozenset()) -> int:
    start, end = as_utc(start), as_utc(end)
    total = 0
    day = start.date()
    while day <= end.date():
        if day.weekday() < 5 and day not in holidays:
            window_start = datetime.combine(day, time(hour=4, minute=30), tzinfo=start.tzinfo)
            window_end = datetime.combine(day, time(hour=12, minute=30), tzinfo=start.tzinfo)
            overlap_start = max(start, window_start)
            overlap_end = min(end, window_end)
            total += max(0, int((overlap_end - overlap_start).total_seconds()))
        day += timedelta(days=1)
    return total


def open_deficiencies(db: Session, application_id: int) -> list[Observation]:
    return db.query(Observation).filter(
        Observation.application_id == application_id,
        Observation.status == "OPEN",
    ).all()


def change_holder(db: Session, application: Application, holder: str, event: str) -> None:
    now = Clock.now()
    active = db.query(SlaSegment).filter(
        SlaSegment.application_id == application.id,
        SlaSegment.ended_at.is_(None),
    ).order_by(SlaSegment.id.desc()).first()
    if active:
        active.ended_at = now
        active.end_event = event
    db.add(SlaSegment(
        application_id=application.id,
        stage=application.stage,
        holder=holder,
        started_at=now,
        start_event=event,
    ))


def _blocked(code: str, message: str, details: dict[str, Any]) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message, "details": details})


def apply_transition(
    db: Session,
    application: Application,
    actor: User,
    event: str,
    expected_version: int,
    reason: str | None,
    request_id: str,
    idempotency_key: str,
    category: str = "DOCUMENTATION",
    commit: bool = True,
) -> Application:
    now = Clock.now()
    existing = db.get(IdempotencyRecord, idempotency_key)
    if existing is not None:
        if existing.application_id != application.id or existing.event != event:
            raise _blocked("IDEMPOTENCY_KEY_REUSED", "This idempotency key belongs to a different request", {"key": idempotency_key})
        return application
    if application.version != expected_version:
        raise _blocked("VERSION_CONFLICT", "The case changed since it was opened", {"expected": expected_version, "current": application.version})

    before = {"stage": application.stage, "status": application.status, "version": application.version}
    old_stage = application.stage
    applicant = actor.role == "INSTITUTION_APPLICANT"
    officer_roles = {"SCRUTINY_OFFICER", "SYSTEM_ADMIN"}
    coordinator_roles = {"EVC_COORDINATOR", "SYSTEM_ADMIN"}

    if event == "ISSUE_DEFICIENCY":
        if old_stage != "SCRUTINY" or actor.role not in officer_roles:
            raise _blocked("TRANSITION_NOT_ALLOWED", "Only a scrutiny officer can issue a deficiency during scrutiny", {"event": event, "stage": old_stage})
        if not reason or not reason.strip():
            raise _blocked("REASON_REQUIRED", "A deficiency reason is required", {"event": event})
        observation = Observation(
            application_id=application.id,
            category=category,
            remarks=reason.strip(),
            status="OPEN",
            created_by=actor.id,
            created_at=now,
        )
        db.add(observation)
        change_holder(db, application, "INSTITUTION", event)
        application.status = "DEFICIENCY_ISSUED"
    elif event == "SUBMIT_RESPONSE":
        if old_stage != "SCRUTINY" or not applicant:
            raise _blocked("TRANSITION_NOT_ALLOWED", "Only the applicant can respond during scrutiny", {"event": event, "stage": old_stage})
        open_items = open_deficiencies(db, application.id)
        if not open_items:
            raise _blocked("PREDICATE_FAILED", "There is no open deficiency to respond to", {"predicate": "open_deficiency"})
        for item in open_items:
            db.add(InstitutionResponse(observation_id=item.id, text=reason or "Synthetic response submitted", submitted_by=actor.id, submitted_at=now))
            item.status = "RESPONDED"
        change_holder(db, application, "AICTE_OFFICER", event)
        application.status = "RESPONSE_SUBMITTED"
    elif event == "COMPLETE_SCRUTINY":
        if old_stage != "SCRUTINY" or actor.role not in officer_roles:
            raise _blocked("TRANSITION_NOT_ALLOWED", "Only a scrutiny officer can complete scrutiny", {"event": event, "stage": old_stage})
        if open_deficiencies(db, application.id):
            raise _blocked("PREDICATE_FAILED", "Open deficiencies must be answered before scrutiny can be completed", {"predicate": "no_open_deficiency"})
        if application.template == "ONLY_SCRUTINY":
            application.stage, application.status = "DONE", "COMPLETED"
        else:
            application.stage, application.status, application.owner_role = "EVC", "IN_PROGRESS", "EVC_COORDINATOR"
        change_holder(db, application, "AICTE_OFFICER", event)
    elif event == "RETURN":
        if old_stage != "EVC" or actor.role not in coordinator_roles:
            raise _blocked("TRANSITION_NOT_ALLOWED", "Only an EVC coordinator can return an EVC case", {"event": event, "stage": old_stage})
        if not reason or not reason.strip():
            raise _blocked("REASON_REQUIRED", "A return reason is required", {"event": event})
        application.stage, application.status, application.owner_role = "SCRUTINY", "RETURNED", "SCRUTINY_OFFICER"
        change_holder(db, application, "AICTE_OFFICER", event)
    elif event in {"CONFIRM_VISIT", "RECORD_EVC_REPORT", "COMPLETE_EVC"}:
        if old_stage != "EVC" or actor.role not in coordinator_roles:
            raise _blocked("TRANSITION_NOT_ALLOWED", "Only an EVC coordinator can update the EVC stage", {"event": event, "stage": old_stage})
        if event == "CONFIRM_VISIT":
            change_holder(db, application, "EXTERNAL_COMMITTEE", event)
        elif event == "RECORD_EVC_REPORT":
            change_holder(db, application, "AICTE_OFFICER", event)
            application.status = "EVC_REPORT_RECEIVED"
        else:
            if application.status != "EVC_REPORT_RECEIVED":
                raise _blocked("PREDICATE_FAILED", "An EVC report is required", {"predicate": "evc_report_received"})
            if application.template == "EVC_SHC":
                application.stage, application.owner_role = "SHC", "SAC_SHC_MEMBER"
            else:
                application.stage, application.owner_role = "DONE", ""
                application.status = "COMPLETED"
            change_holder(db, application, "AICTE_OFFICER", event)
    else:
        raise _blocked("TRANSITION_NOT_ALLOWED", "The requested event is not available for this case", {"event": event, "stage": old_stage})

    application.version += 1
    application.updated_at = now
    append_event(
        db,
        actor.id,
        event,
        "application",
        application.reference_no,
        before,
        {"stage": application.stage, "status": application.status, "version": application.version},
        reason,
        request_id,
    )
    db.add(IdempotencyRecord(
        key=idempotency_key,
        application_id=application.id,
        event=event,
        resulting_version=application.version,
    ))
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(application)
    return application


def sla_totals(db: Session, application_id: int) -> dict[str, int]:
    now = Clock.now()
    totals: dict[str, int] = {}
    holiday_config = db.get(AppConfig, "demo_holidays")
    holidays = frozenset(date.fromisoformat(value) for value in json.loads(holiday_config.value_json)) if holiday_config else frozenset()
    segments = db.query(SlaSegment).filter(SlaSegment.application_id == application_id).all()
    for segment in segments:
        end = segment.ended_at or now
        totals[segment.holder] = totals.get(segment.holder, 0) + business_seconds(segment.started_at, end, holidays)
    return totals
