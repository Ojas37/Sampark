import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .clock import Clock
from .db import Base, engine, ensure_compatible_schema
from .models import (
    AppConfig,
    Application,
    CalendarHoliday,
    ConflictRecord,
    Document,
    EvcPlan,
    EvcPlanAssignment,
    Expert,
    ExpertAvailability,
    Institution,
    InstitutionResponse,
    IdempotencyRecord,
    Notification,
    Observation,
    Region,
    SlaSegment,
    Undertaking,
    User,
    WorkflowDefinition,
)
from .security import hash_password
from .services.audit import append_event
from .services.obligations import compute_sha256


ROLES = [
    "INSTITUTION_APPLICANT",
    "SCRUTINY_OFFICER",
    "EVC_COORDINATOR",
    "EVC_EXPERT",
    "SAC_SHC_MEMBER",
    "REGIONAL_OFFICER",
    "COMPLIANCE_OFFICER",
    "SENIOR_MANAGEMENT",
    "SYSTEM_ADMIN",
    "SECOND_APPROVER",
    "AUDITOR",
]
REGIONS = [
    ("WR", "Western Region", 19.08, 72.88),
    ("SR", "Southern Region", 13.08, 80.27),
    ("ER", "Eastern Region", 22.57, 88.36),
    ("NR", "Northern Region", 28.61, 77.21),
]


def seed_database(db: Session) -> None:
    Base.metadata.create_all(bind=engine)
    ensure_compatible_schema()
    for table in reversed(list(Base.metadata.sorted_tables)):
        db.execute(table.delete())
    db.expunge_all()
    Clock.reset()
    for code, name, latitude, longitude in REGIONS:
        db.add(Region(code=code, name=name, latitude=latitude, longitude=longitude))
    db.flush()
    for holiday in [
        ("2026-11-02", "Synthetic demo closure 01"),
        ("2026-11-11", "Synthetic demo closure 02"),
        ("2026-11-20", "Synthetic demo closure 03"),
    ]:
        db.add(CalendarHoliday(date=date.fromisoformat(holiday[0]), label=holiday[1], tag="placeholder"))
    institutions: list[Institution] = []
    for index in range(1, 13):
        institution = Institution(
            name=f"Demo Institute of Technology {index:02}",
            region_code="NR" if index == 1 else REGIONS[(index - 1) % 4][0],
            identifier=f"DEMO-{index:04}",
        )
        db.add(institution)
        institutions.append(institution)
    db.flush()

    users: list[User] = []
    for role in ROLES:
        institution_id = institutions[0].id if role == "INSTITUTION_APPLICANT" else None
        region_code = "NR" if role in {"SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_OFFICER"} else None
        user = User(
            name=role.replace("_", " ").title(),
            email=f"{role.lower()}@demo.test",
            password_hash=hash_password("demo1234"),
            role=role,
            region_code=region_code,
            institution_id=institution_id,
        )
        db.add(user)
        users.append(user)
    db.flush()
    role_users = {user.role: user for user in users}
    now = Clock.now()

    for index in range(1, 16):
        primary_tag = ["CIVIL", "MECH", "ELEC", "CSE", "MGMT", "ARCH"][(index - 1) % 6]
        secondary_tag = ["CIVIL", "MECH", "ELEC", "CSE", "MGMT", "ARCH"][index % 6]
        expert = Expert(
            name=f"Demo Expert {index:02}",
            home_region=REGIONS[(index - 1) % 4][0],
            tags=f"{primary_tag},{secondary_tag}",
            max_visits=3,
        )
        db.add(expert)
    db.flush()
    for index, expert in enumerate(db.query(Expert).order_by(Expert.id).limit(6).all()):
        db.add(ConflictRecord(expert_id=expert.id, institution_id=institutions[(index * 5) % 12].id, reason="Synthetic declared conflict"))
    workdays = []
    candidate_day = now.date()
    while len(workdays) < 10:
        candidate_day += timedelta(days=1)
        if candidate_day.weekday() < 5 and candidate_day not in {date(2026, 11, 2), date(2026, 11, 11), date(2026, 11, 20)}:
            workdays.append(candidate_day)
    for expert in db.query(Expert).order_by(Expert.id).all():
        for day_index, available_date in enumerate(workdays):
            available = not (
                (expert.id == 14 and day_index in {2, 3, 7})
                or (expert.id == 15 and day_index in {1, 5, 8})
                or (expert.id % 5 == day_index % 5)
            )
            db.add(ExpertAvailability(expert_id=expert.id, available_date=available_date, available=available))

    for index in range(1, 41):
        if index == 1:
            stage, template, status, region = "SCRUTINY", "SCRUTINY_EVC", "IN_PROGRESS", "NR"
        elif index == 2:
            stage, template, status, region = "SCRUTINY", "SCRUTINY_EVC", "IN_PROGRESS", "NR"
        elif index == 3:
            stage, template, status, region = "SCRUTINY", "SCRUTINY_EVC", "DEFICIENCY_ISSUED", "NR"
        elif 4 <= index <= 33:
            stage, template, status, region = "EVC", "SCRUTINY_EVC", "IN_PROGRESS", REGIONS[(index - 1) % 4][0]
        elif index <= 36:
            stage, template, status, region = "SHC", "EVC_SHC", "IN_PROGRESS", REGIONS[(index - 1) % 4][0]
        else:
            stage, template, status, region = "DONE", "ONLY_SCRUTINY", "COMPLETED", REGIONS[(index - 1) % 4][0]
        institution = institutions[0] if index <= 3 else institutions[(index - 1) % len(institutions)]
        created_at = now - timedelta(days=2 if index == 1 else 18 if index == 2 else index % 20 + 1)
        application = Application(
            reference_no=f"FW-2026-{index:04}",
            institution_id=institution.id,
            region_code=region,
            application_type="INTAKE_OR_COURSE" if index % 2 else "NEW_PROGRAM_OR_LEVEL",
            template=template,
            template_version=1,
            stage=stage,
            status=status,
            owner_role="SCRUTINY_OFFICER" if stage == "SCRUTINY" else "EVC_COORDINATOR" if stage == "EVC" else "SAC_SHC_MEMBER" if stage == "SHC" else "",
            priority=(index % 5) + 1,
            visit_mode=["physical", "online", "hybrid"][index % 3],
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(application)
        db.flush()
        holder = "INSTITUTION" if index == 3 else "AICTE_OFFICER" if stage == "SCRUTINY" else "SYSTEM"
        started_at = now - timedelta(days=8 if index == 3 else 17 if index == 2 else 1)
        db.add(SlaSegment(application_id=application.id, stage=stage, holder=holder, started_at=started_at, start_event="SEEDED"))
        if index == 3:
            db.add(Observation(
                application_id=application.id,
                category="DOCUMENTATION",
                remarks="Synthetic demo deficiency: provide a current campus document.",
                status="OPEN",
                created_by=role_users["SCRUTINY_OFFICER"].id,
                created_at=started_at,
            ))
        if index <= 3:
            append_event(db, role_users["SYSTEM_ADMIN"].id, "SEEDED", "application", application.reference_no, after={"stage": stage, "status": status})
    db.flush()
    for index in range(3):
        db.add(Undertaking(
            institution_id=institutions[index].id,
            title=["Submit synthetic compliance undertaking", "Renew synthetic lease document", "Provide annual report"][index],
            application_id=None,
            due_at=now + timedelta(days=[6, -2, 24][index]),
            status=["DUE_SOON", "OVERDUE", "NOT_DUE"][index],
        ))
    seed_documents(db, institutions)
    seed_workflow_definitions(db, role_users)
    for key, value, tag in [
        ("demo_clock_offset_seconds", "0", "placeholder"),
        ("demo_holidays", '["2026-11-02","2026-11-11","2026-11-20"]', "placeholder"),
        ("sla_hours_scrutiny", "120", "placeholder"),
        ("sla_hours_evc", "240", "placeholder"),
        ("visit_mode_rules", '["physical","online","hybrid"]', "sourced_verify"),
        ("visit_window_days", "10", "placeholder"),
        ("business_hours_ist", '{"start":"10:00","end":"18:00","timezone":"Asia/Kolkata","weekdays":[0,1,2,3,4]}', "placeholder"),
        ("evc_constitution", '"Constituted by the Council"', "sourced_verify"),
        ("appeal_window_days", "7", "sourced_verify"),
        ("state_university_view_days", "21", "sourced_verify"),
        ("approval_cutoff", '"30 April"', "sourced_verify"),
        ("priority_weights", '{"sla_pressure":0.35,"escalation_level":0.2,"obligation_urgency":0.15,"evc_readiness":0.1,"case_age":0.1,"blocking_others":0.1}', "placeholder"),
    ]:
        db.add(AppConfig(key=key, value_json=value, tag=tag, version=1))
    db.commit()


# Synthetic documents with a text layer and known ground-truth obligations.
# Every clause is deliberately phrased so the rule-based extractor grounds its
# quote verbatim on the cited page. All content is synthetic and labelled.
SEED_DOCUMENTS = [
    {
        "filename": "approval_letter_DEMO-0001.pdf",
        "doc_type": "approval_letter",
        "doc_date": date(2026, 10, 12),
        "institution_index": 0,
        "pages": [
            "SYNTHETIC APPROVAL LETTER (DEMO DATA ONLY).\n"
            "All India Council for Technical Education.\n"
            "Date of issue: 2026-10-12.\n"
            "This Letter of Approval is granted to the institution subject to the conditions stated below.\n"
            "The institution shall submit the registered lease deed for the permanent campus within 90 days of issue.\n"
            "The institution shall submit a valid fire safety certificate within 60 days of issue.",
            "Further conditions apply as a continuing requirement.\n"
            "The institution shall appoint faculty to meet the prescribed student-faculty ratio before the commencement of the session.\n"
            "The institution shall furnish the bank guarantee as specified within 45 days of issue.\n"
            "The approved lease is valid up to 2036-03-31 as per the submitted documents.\n"
            "This is a synthetic document generated for the Smart India Hackathon demonstration.",
        ],
    },
    {
        "filename": "lease_deed_DEMO-0002.pdf",
        "doc_type": "lease_deed",
        "doc_date": date(2026, 9, 1),
        "institution_index": 1,
        "pages": [
            "SYNTHETIC LEASE DEED (DEMO DATA ONLY).\n"
            "This lease deed is executed for the campus land of the institution.\n"
            "The lease commences on 2026-09-01 and the lease expiry is 2034-08-31.\n"
            "The lessee shall submit the registered lease document for the campus to the authority within 30 days of issue.\n"
            "This is synthetic content for demonstration only.",
        ],
    },
    {
        "filename": "evc_report_DEMO-0003.pdf",
        "doc_type": "evc_report",
        "doc_date": date(2026, 10, 20),
        "institution_index": 2,
        "pages": [
            "SYNTHETIC EXPERT VISIT COMMITTEE REPORT (DEMO DATA ONLY).\n"
            "Date of report: 2026-10-20.\n"
            "The committee observed that the building completion certificate must be submitted within 15 days of issue.\n"
            "The institution shall file the mandatory annual report within 180 days of issue.\n"
            "The affiliation approval from the affiliating body is valid until 2029-06-30.\n"
            "This report is synthetic and generated for the hackathon demonstration.",
        ],
    },
]


SEED_WORKFLOWS = {
    "ONLY_SCRUTINY": {
        "start": "SCRUTINY",
        "stages": [
            {"code": "SCRUTINY", "role": "SCRUTINY_OFFICER", "sla_hours": 120, "type": "task"},
            {"code": "DONE", "type": "terminal"},
        ],
        "transitions": [
            {"from": "SCRUTINY", "to": "DONE", "event": "COMPLETE_SCRUTINY", "when": {"all": [{"pred": "no_open_deficiency"}, {"pred": "docs_verified"}]}},
        ],
    },
    "SCRUTINY_EVC": {
        "start": "SCRUTINY",
        "stages": [
            {"code": "SCRUTINY", "role": "SCRUTINY_OFFICER", "sla_hours": 120, "type": "task"},
            {"code": "EVC", "role": "EVC_COORDINATOR", "sla_hours": 240, "type": "task"},
            {"code": "DONE", "type": "terminal"},
        ],
        "transitions": [
            {"from": "SCRUTINY", "to": "EVC", "event": "COMPLETE_SCRUTINY", "when": {"all": [{"pred": "no_open_deficiency"}, {"pred": "docs_verified"}]}},
            {"from": "EVC", "to": "DONE", "event": "COMPLETE_EVC", "when": {"pred": "evc_report_received"}},
            {"from": "EVC", "to": "SCRUTINY", "event": "RETURN", "requires_reason": True},
        ],
    },
    "EVC_SHC": {
        "start": "EVC",
        "stages": [
            {"code": "EVC", "role": "EVC_COORDINATOR", "sla_hours": 240, "type": "task"},
            {"code": "SHC", "role": "SAC_SHC_MEMBER", "sla_hours": 120, "type": "task"},
            {"code": "DONE", "type": "terminal"},
        ],
        "transitions": [
            {"from": "EVC", "to": "SHC", "event": "COMPLETE_EVC", "when": {"pred": "evc_report_received"}},
            {"from": "SHC", "to": "DONE", "event": "RECORD_RECOMMENDATION", "when": {"pred": "shc_recommendation_recorded"}},
        ],
    },
    "ONLY_EVC": {
        "start": "EVC",
        "stages": [
            {"code": "EVC", "role": "EVC_COORDINATOR", "sla_hours": 240, "type": "task"},
            {"code": "DONE", "type": "terminal"},
        ],
        "transitions": [
            {"from": "EVC", "to": "DONE", "event": "COMPLETE_EVC", "when": {"pred": "evc_report_received"}},
        ],
    },
}


def seed_workflow_definitions(db: Session, role_users: dict) -> None:
    now = Clock.now()
    admin = role_users["SYSTEM_ADMIN"]
    approver = role_users["SECOND_APPROVER"]
    for code, graph in SEED_WORKFLOWS.items():
        db.add(WorkflowDefinition(
            template_code=code,
            version=1,
            status="PUBLISHED",
            graph_json=json.dumps(graph),
            proposed_by=admin.id,
            approved_by=approver.id,
            created_at=now,
            updated_at=now,
        ))


def seed_documents(db: Session, institutions: list[Institution]) -> None:
    now = Clock.now()
    for spec in SEED_DOCUMENTS:
        institution = institutions[spec["institution_index"]]
        db.add(Document(
            institution_id=institution.id,
            application_id=None,
            filename=spec["filename"],
            doc_type=spec["doc_type"],
            doc_date=spec["doc_date"],
            sha256=compute_sha256(spec["pages"]),
            pages_json=json.dumps(spec["pages"]),
            source="synthetic_seed",
            uploaded_by=None,
            created_at=now,
        ))
