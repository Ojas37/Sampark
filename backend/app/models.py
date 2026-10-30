from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(40), index=True)
    region_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Region(Base):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class CalendarHoliday(Base):
    __tablename__ = "calendar_holidays"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    tag: Mapped[str] = mapped_column(String(20), default="placeholder")


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(140), unique=True)
    region_code: Mapped[str] = mapped_column(ForeignKey("regions.code"), index=True)
    identifier: Mapped[str] = mapped_column(String(40), unique=True)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    region_code: Mapped[str] = mapped_column(ForeignKey("regions.code"), index=True)
    application_type: Mapped[str] = mapped_column(String(60))
    academic_year: Mapped[str] = mapped_column(String(12), default="2026-27")
    template: Mapped[str] = mapped_column(String(40))
    template_version: Mapped[int] = mapped_column(Integer, default=1)
    stage: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    owner_role: Mapped[str] = mapped_column(String(40))
    priority: Mapped[int] = mapped_column(Integer, default=3)
    visit_mode: Mapped[str] = mapped_column(String(20), default="physical")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class Observation(Base):
    __tablename__ = "scrutiny_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    remarks: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InstitutionResponse(Base):
    __tablename__ = "institution_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("scrutiny_observations.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SlaSegment(Base):
    __tablename__ = "sla_clock_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    holder: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_event: Mapped[str] = mapped_column(String(60))
    end_event: Mapped[str | None] = mapped_column(String(60), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80))
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str] = mapped_column(String(40), default="")
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), index=True)


class Undertaking(Base):
    __tablename__ = "undertakings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="NOT_DUE")
    source: Mapped[str] = mapped_column(String(80), default="Synthetic demo seed")


class Expert(Base):
    __tablename__ = "evc_experts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    home_region: Mapped[str] = mapped_column(String(2))
    tags: Mapped[str] = mapped_column(String(200))
    max_visits: Mapped[int] = mapped_column(Integer, default=3)


class ExpertAvailability(Base):
    __tablename__ = "expert_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expert_id: Mapped[int] = mapped_column(ForeignKey("evc_experts.id"), index=True)
    available_date: Mapped[date] = mapped_column(Date, index=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class EvcPlan(Base):
    __tablename__ = "evc_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    params_json: Mapped[str] = mapped_column(Text)
    solver_status: Mapped[str] = mapped_column(String(20))
    metrics_json: Mapped[str] = mapped_column(Text)
    baseline_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PROPOSED")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvcPlanAssignment(Base):
    __tablename__ = "evc_plan_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("evc_plans.id"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    panel_json: Mapped[str] = mapped_column(Text)
    visit_mode: Mapped[str] = mapped_column(String(20))
    explanation_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PROPOSED")


class ConflictRecord(Base):
    __tablename__ = "coi_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expert_id: Mapped[int] = mapped_column(ForeignKey("evc_experts.id"))
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    reason: Mapped[str] = mapped_column(String(200))


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    tag: Mapped[str] = mapped_column(String(20), default="placeholder")
    version: Mapped[int] = mapped_column(Integer, default=1)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80))
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    subject: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="SIMULATED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    event: Mapped[str] = mapped_column(String(60))
    resulting_version: Mapped[int] = mapped_column(Integer)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(40), default="approval_letter")
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    pages_json: Mapped[str] = mapped_column(Text)  # list of page text strings
    source: Mapped[str] = mapped_column(String(40), default="synthetic_seed")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="rule_based")
    model: Mapped[str] = mapped_column(String(60), default="flowwise-rules-v1")
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    candidates_total: Mapped[int] = mapped_column(Integer, default=0)
    candidates_grounded: Mapped[int] = mapped_column(Integer, default=0)
    candidates_discarded: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Letter(Base):
    __tablename__ = "letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    letter_type: Mapped[str] = mapped_column(String(40), default="deficiency_notice")
    reference_no: Mapped[str] = mapped_column(String(40), index=True)
    verify_token: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="valid")  # valid | superseded | withdrawn
    file_path: Mapped[str] = mapped_column(String(300))
    issued_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_code: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")  # DRAFT|VALIDATED|SUBMITTED_FOR_APPROVAL|PUBLISHED|REJECTED|RETIRED
    graph_json: Mapped[str] = mapped_column(Text)
    proposed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ObligationCandidate(Base):
    __tablename__ = "obligation_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("extraction_runs.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="obligation")  # obligation | validity
    category: Mapped[str] = mapped_column(String(40), default="UNDERTAKING")
    description: Mapped[str] = mapped_column(Text)
    responsible_party: Mapped[str] = mapped_column(String(40), default="INSTITUTION")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_expression: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    field_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, default=1)
    source_quote: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    grounded: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING | ACCEPTED | REJECTED
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
