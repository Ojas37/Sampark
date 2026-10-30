import json
import uuid
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .clock import Clock, as_utc
from .config import settings
from .db import Base, SessionLocal, engine, ensure_compatible_schema, get_db
from datetime import date

from .models import (
    AppConfig,
    Application,
    AuditEvent,
    Document,
    Expert,
    EvcPlan,
    EvcPlanAssignment,
    ExtractionRun,
    Institution,
    InstitutionResponse,
    Letter,
    Notification,
    ObligationCandidate,
    Observation,
    Region,
    SlaSegment,
    Undertaking,
    User,
    WorkflowDefinition,
)
from .schemas import (
    CandidateDecisionRequest,
    ClockAdvanceRequest,
    DocumentUploadRequest,
    LoginRequest,
    ObservationRequest,
    ResponseRequest,
    LetterRequest,
    SimulationRequest,
    TransitionRequest,
    WorkflowDraftRequest,
    WorkflowRejectRequest,
    WorkflowValidateRequest,
)
from .security import (
    DbSession,
    create_access_token,
    current_user,
    ensure_case_scope,
    require,
    verify_password,
)
from .seed import seed_database
from .services.audit import append_event, tamper_first_event, verify_chain
import hashlib

from .services.letters import generate_letter, verify_letter
from .services.obligations import accept_candidate, compute_sha256, reject_candidate, run_extraction
from .services.planner import confirm_evc_plan, create_evc_plan
from .services import studio
from .services.simulator import run_simulation
from .services.workflow import WORKFLOW_TEMPLATES, apply_transition, open_deficiencies, sla_totals


Base.metadata.create_all(bind=engine)
ensure_compatible_schema()
app = FastAPI(title="AICTE FlowWise API", version="0.1.0", description="Synthetic SIH prototype. No AICTE systems are connected.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and {"code", "message", "details"} <= detail.keys():
        payload = {"error": detail}
    else:
        payload = {"error": {"code": "REQUEST_FAILED", "message": str(detail), "details": {}}}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid", "details": exc.errors()}})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "The request could not be completed", "details": {"type": type(exc).__name__}}})


def serialize_application(db: Session, item: Application) -> dict[str, Any]:
    institution = db.get(Institution, item.institution_id)
    open_count = len(open_deficiencies(db, item.id))
    return {
        "id": item.id,
        "reference_no": item.reference_no,
        "institution": institution.name if institution else "Synthetic institution",
        "institution_id": item.institution_id,
        "region_code": item.region_code,
        "application_type": item.application_type,
        "template": item.template,
        "template_version": item.template_version,
        "stage": item.stage,
        "status": item.status,
        "owner_role": item.owner_role,
        "priority": item.priority,
        "visit_mode": item.visit_mode,
        "created_at": item.created_at.isoformat(),
        "version": item.version,
        "open_deficiencies": open_count,
    }


def require_application(db: Session, application_id: int, user: User) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Application not found", "details": {}})
    ensure_case_scope(user, application)
    return application


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, db: DbSession) -> dict[str, Any]:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect", "details": {}})
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_payload(user)}


def user_payload(user: User) -> dict[str, Any]:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "region_code": user.region_code, "institution_id": user.institution_id}


@app.get("/api/v1/auth/me")
def me(user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    return user_payload(user)


@app.get("/api/v1/demo/accounts")
def demo_accounts(db: DbSession) -> list[dict[str, str]]:
    return [
        {"email": user.email, "role": user.role, "password": "demo1234"}
        for user in db.query(User).order_by(User.role).all()
    ]


@app.get("/api/v1/dashboard/summary")
def dashboard(db: DbSession, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    query = db.query(Application)
    if user.role == "INSTITUTION_APPLICANT":
        query = query.filter(Application.institution_id == user.institution_id)
    elif user.region_code and user.role in {"SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_OFFICER"}:
        query = query.filter(Application.region_code == user.region_code)
    applications = query.all()
    by_stage: dict[str, int] = {}
    for item in applications:
        by_stage[item.stage] = by_stage.get(item.stage, 0) + 1
    return {
        "total": len(applications),
        "active": sum(item.stage != "DONE" for item in applications),
        "evc_ready": sum(item.stage == "EVC" for item in applications),
        "open_deficiencies": sum(len(open_deficiencies(db, item.id)) for item in applications),
        "overdue_undertakings": db.query(Undertaking).filter(Undertaking.status == "OVERDUE").count(),
        "by_stage": by_stage,
        "regions": [{"code": region.code, "name": region.name} for region in db.query(Region).all()],
    }


@app.get("/api/v1/applications")
def list_applications(
    db: DbSession,
    user: Annotated[User, Depends(current_user)],
    stage: str | None = None,
    region: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    query = db.query(Application)
    if user.role == "INSTITUTION_APPLICANT":
        query = query.filter(Application.institution_id == user.institution_id)
    elif user.region_code and user.role in {"SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_OFFICER"}:
        query = query.filter(Application.region_code == user.region_code)
    if stage:
        query = query.filter(Application.stage == stage.upper())
    if region and user.role not in {"INSTITUTION_APPLICANT"}:
        query = query.filter(Application.region_code == region.upper())
    if q:
        query = query.filter(Application.reference_no.contains(q))
    return [serialize_application(db, item) for item in query.order_by(Application.priority.desc(), Application.created_at.asc()).limit(200)]


@app.get("/api/v1/applications/{application_id}")
def get_application(application_id: int, db: DbSession, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    return serialize_application(db, require_application(db, application_id, user))


@app.get("/api/v1/applications/{application_id}/timeline")
def timeline(application_id: int, db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    item = require_application(db, application_id, user)
    events = db.query(AuditEvent).filter(
        AuditEvent.entity_type == "application",
        AuditEvent.entity_id == item.reference_no,
    ).order_by(AuditEvent.id.desc()).limit(100).all()
    return [{"id": event.id, "action": event.action, "reason": event.reason, "occurred_at": event.occurred_at.isoformat(), "actor_id": event.actor_id} for event in events]


@app.get("/api/v1/applications/{application_id}/sla")
def sla(application_id: int, db: DbSession, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    item = require_application(db, application_id, user)
    segments = db.query(SlaSegment).filter(SlaSegment.application_id == item.id).order_by(SlaSegment.id.asc()).all()
    now = Clock.now()
    return {
        "totals_seconds": sla_totals(db, item.id),
        "segments": [
            {
                "holder": segment.holder,
                "stage": segment.stage,
                "started_at": as_utc(segment.started_at).isoformat(),
                "ended_at": as_utc(segment.ended_at).isoformat() if segment.ended_at else None,
                "elapsed_seconds": max(
                    0,
                    int(((as_utc(segment.ended_at) if segment.ended_at else now) - as_utc(segment.started_at)).total_seconds()),
                ),
            }
            for segment in segments
        ],
    }


@app.post("/api/v1/applications/{application_id}/transitions")
def transition(
    application_id: int,
    payload: TransitionRequest,
    db: DbSession,
    user: Annotated[User, Depends(current_user)],
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide an Idempotency-Key header", "details": {}})
    application = require_application(db, application_id, user)
    if user.role == "INSTITUTION_APPLICANT" and payload.event != "SUBMIT_RESPONSE":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_ROLE", "message": "Applicants may only submit deficiency responses", "details": {}})
    try:
        updated = apply_transition(db, application, user, payload.event.upper(), payload.expected_version, payload.reason, request.state.request_id, idempotency_key)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return serialize_application(db, updated)


@app.post("/api/v1/applications/{application_id}/observations")
def add_observation(
    application_id: int,
    payload: ObservationRequest,
    db: DbSession,
    user: Annotated[User, Depends(require("SCRUTINY_OFFICER", "SYSTEM_ADMIN"))],
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide an Idempotency-Key header", "details": {}})
    item = require_application(db, application_id, user)
    try:
        updated = apply_transition(db, item, user, "ISSUE_DEFICIENCY", item.version, payload.remarks, request.state.request_id, idempotency_key, payload.category)
    except Exception:
        db.rollback()
        raise
    observation = db.query(Observation).filter(Observation.application_id == updated.id).order_by(Observation.id.desc()).first()
    return {"id": observation.id if observation else None, "category": payload.category, "remarks": payload.remarks, "application": serialize_application(db, updated)}


@app.post("/api/v1/applications/{application_id}/responses")
def respond(
    application_id: int,
    payload: ResponseRequest,
    db: DbSession,
    user: Annotated[User, Depends(current_user)],
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide an Idempotency-Key header", "details": {}})
    item = require_application(db, application_id, user)
    observation = db.get(Observation, payload.observation_id)
    if observation is None or observation.application_id != item.id or observation.status != "OPEN":
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Open observation not found", "details": {}})
    result = apply_transition(db, item, user, "SUBMIT_RESPONSE", item.version, payload.text, request.state.request_id, idempotency_key)
    return {"application": serialize_application(db, result), "message": "Response recorded for officer review"}


@app.get("/api/v1/applications/{application_id}/observations")
def list_observations(application_id: int, db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    item = require_application(db, application_id, user)
    observations = db.query(Observation).filter(Observation.application_id == item.id).order_by(Observation.id.desc()).all()
    result = []
    for observation in observations:
        response = db.query(InstitutionResponse).filter(InstitutionResponse.observation_id == observation.id).order_by(InstitutionResponse.id.desc()).first()
        result.append({"id": observation.id, "category": observation.category, "remarks": observation.remarks, "status": observation.status, "response": response.text if response else None})
    return result


@app.get("/api/v1/workflow-templates")
def templates(_: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    return WORKFLOW_TEMPLATES


def _definition_with_names(db: Session, definition: WorkflowDefinition) -> dict[str, Any]:
    proposer = db.get(User, definition.proposed_by) if definition.proposed_by else None
    approver = db.get(User, definition.approved_by) if definition.approved_by else None
    return studio.serialize_definition(definition, proposer.name if proposer else None, approver.name if approver else None)


@app.get("/api/v1/workflow-definitions")
def list_definitions(db: DbSession, _: Annotated[User, Depends(require("SYSTEM_ADMIN", "SECOND_APPROVER", "AUDITOR"))]) -> list[dict[str, Any]]:
    definitions = db.query(WorkflowDefinition).order_by(WorkflowDefinition.template_code, WorkflowDefinition.version.desc()).all()
    return [_definition_with_names(db, definition) for definition in definitions]


@app.post("/api/v1/workflow-definitions/validate")
def validate_definition(payload: WorkflowValidateRequest, _: Annotated[User, Depends(require("SYSTEM_ADMIN", "SECOND_APPROVER"))]) -> dict[str, Any]:
    return {"validation": studio.validate_graph(payload.graph), "dry_run": studio.dry_run(payload.graph)}


@app.post("/api/v1/workflow-definitions")
def create_workflow_draft(payload: WorkflowDraftRequest, db: DbSession, user: Annotated[User, Depends(require("SYSTEM_ADMIN"))], request: Request) -> dict[str, Any]:
    validation = studio.validate_graph(payload.graph)
    definition = studio.create_draft(db, user, payload.template_code.upper(), payload.graph, request.state.request_id)
    result = _definition_with_names(db, definition)
    result["validation"] = validation
    return result


@app.post("/api/v1/workflow-definitions/{definition_id}/submit")
def submit_workflow(definition_id: int, db: DbSession, user: Annotated[User, Depends(require("SYSTEM_ADMIN"))], request: Request) -> dict[str, Any]:
    definition = db.get(WorkflowDefinition, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Definition not found", "details": {}})
    try:
        studio.submit_for_approval(db, user, definition, request.state.request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "SUBMIT_BLOCKED", "message": str(exc), "details": {}})
    return _definition_with_names(db, definition)


@app.post("/api/v1/workflow-definitions/{definition_id}/publish")
def publish_workflow(definition_id: int, db: DbSession, user: Annotated[User, Depends(require("SECOND_APPROVER", "SYSTEM_ADMIN"))], request: Request) -> dict[str, Any]:
    definition = db.get(WorkflowDefinition, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Definition not found", "details": {}})
    try:
        studio.publish(db, user, definition, request.state.request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "PUBLISH_BLOCKED", "message": str(exc), "details": {}})
    return _definition_with_names(db, definition)


@app.post("/api/v1/workflow-definitions/{definition_id}/reject")
def reject_workflow(definition_id: int, payload: WorkflowRejectRequest, db: DbSession, user: Annotated[User, Depends(require("SECOND_APPROVER", "SYSTEM_ADMIN"))], request: Request) -> dict[str, Any]:
    definition = db.get(WorkflowDefinition, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Definition not found", "details": {}})
    try:
        studio.reject(db, user, definition, payload.reason, request.state.request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "REJECT_BLOCKED", "message": str(exc), "details": {}})
    return _definition_with_names(db, definition)


@app.get("/api/v1/institutions")
def institutions(db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    query = db.query(Institution)
    if user.role == "INSTITUTION_APPLICANT":
        query = query.filter(Institution.id == user.institution_id)
    return [{"id": item.id, "name": item.name, "region_code": item.region_code, "identifier": item.identifier} for item in query.order_by(Institution.id)]


@app.get("/api/v1/evc/queue")
def evc_queue(db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    if user.role not in {"EVC_COORDINATOR", "SYSTEM_ADMIN", "REGIONAL_OFFICER", "SENIOR_MANAGEMENT"}:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_ROLE", "message": "Your role cannot access the EVC queue", "details": {}})
    query = db.query(Application).filter(Application.stage == "EVC")
    if user.region_code:
        query = query.filter(Application.region_code == user.region_code)
    return [serialize_application(db, item) for item in query.order_by(Application.priority.desc(), Application.created_at.asc())]


@app.get("/api/v1/experts")
def experts(db: DbSession, _: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    return [{"id": expert.id, "name": expert.name, "home_region": expert.home_region, "tags": expert.tags.split(","), "max_visits": expert.max_visits} for expert in db.query(Expert).order_by(Expert.id)]


@app.post("/api/v1/evc/plans")
def create_plan(
    db: DbSession,
    user: Annotated[User, Depends(require("EVC_COORDINATOR", "SYSTEM_ADMIN", "REGIONAL_OFFICER"))],
    request: Request,
) -> dict[str, Any]:
    try:
        return create_evc_plan(db, user, request.state.request_id)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail={"code": "PLANNER_UNAVAILABLE", "message": "No feasible EVC proposal could be generated", "details": {"reason": str(exc)}})


@app.get("/api/v1/evc/plans/{plan_id}")
def get_plan(
    plan_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require("EVC_COORDINATOR", "SYSTEM_ADMIN", "REGIONAL_OFFICER", "SENIOR_MANAGEMENT"))],
) -> dict[str, Any]:
    plan = db.get(EvcPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "EVC plan not found", "details": {}})
    query = db.query(EvcPlanAssignment, Application).join(
        Application, Application.id == EvcPlanAssignment.application_id
    ).filter(EvcPlanAssignment.plan_id == plan.id)
    if user.region_code:
        query = query.filter(Application.region_code == user.region_code)
    rows = query.order_by(EvcPlanAssignment.id).all()
    return {
        "plan_id": plan.id,
        "status": plan.status,
        "solver_status": plan.solver_status,
        "window_start": plan.window_start.isoformat(),
        "window_end": plan.window_end.isoformat(),
        "metrics": json.loads(plan.metrics_json),
        "assignments": [json.loads(row.explanation_json) for row, _ in rows],
    }


@app.get("/api/v1/evc/plans/{plan_id}/baseline")
def get_plan_baseline(
    plan_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require("EVC_COORDINATOR", "SYSTEM_ADMIN", "REGIONAL_OFFICER", "SENIOR_MANAGEMENT"))],
) -> dict[str, Any]:
    plan = db.get(EvcPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "EVC plan not found", "details": {}})
    if user.region_code:
        raise HTTPException(status_code=403, detail={"code": "REGION_SCOPED_BASELINE", "message": "The stored baseline is not available across region scopes", "details": {}})
    return {"plan_id": plan.id, "method": "Greedy oldest-first", "metrics": json.loads(plan.baseline_json)}


@app.post("/api/v1/evc/plans/{plan_id}/confirm")
def confirm_plan(
    plan_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require("EVC_COORDINATOR", "SYSTEM_ADMIN"))],
    request: Request,
) -> dict[str, Any]:
    try:
        return confirm_evc_plan(db, user, plan_id, request.state.request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "PLAN_CONFIRMATION_BLOCKED", "message": str(exc), "details": {"plan_id": plan_id}})


@app.get("/api/v1/undertakings")
def undertakings(db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    query = db.query(Undertaking, Institution).join(Institution, Institution.id == Undertaking.institution_id)
    if user.role == "INSTITUTION_APPLICANT":
        query = query.filter(Undertaking.institution_id == user.institution_id)
    return [{"id": row.id, "title": row.title, "institution": institution.name, "due_at": row.due_at.isoformat(), "status": row.status, "source": row.source} for row, institution in query.order_by(Undertaking.due_at)]


@app.get("/api/v1/notifications")
def notifications(db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    query = db.query(Notification)
    if user.role not in {"SYSTEM_ADMIN", "AUDITOR"}:
        query = query.filter(Notification.recipient_id == user.id)
    return [
        {"id": item.id, "entity_type": item.entity_type, "entity_id": item.entity_id, "channel": item.channel, "subject": item.subject, "body": item.body, "status": item.status, "created_at": item.created_at.isoformat()}
        for item in query.order_by(Notification.id.desc()).limit(200)
    ]


def serialize_candidate(candidate: ObligationCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "run_id": candidate.run_id,
        "document_id": candidate.document_id,
        "kind": candidate.kind,
        "category": candidate.category,
        "description": candidate.description,
        "responsible_party": candidate.responsible_party,
        "due_date": candidate.due_date.isoformat() if candidate.due_date else None,
        "due_expression": candidate.due_expression,
        "field_name": candidate.field_name,
        "field_value": candidate.field_value,
        "source_page": candidate.source_page,
        "source_quote": candidate.source_quote,
        "confidence": candidate.confidence,
        "grounded": candidate.grounded,
        "status": candidate.status,
        "edited": candidate.edited,
    }


def serialize_document(db: Session, document: Document) -> dict[str, Any]:
    institution = db.get(Institution, document.institution_id) if document.institution_id else None
    pending = db.query(ObligationCandidate).filter(
        ObligationCandidate.document_id == document.id,
        ObligationCandidate.status == "PENDING",
    ).count()
    accepted = db.query(ObligationCandidate).filter(
        ObligationCandidate.document_id == document.id,
        ObligationCandidate.status == "ACCEPTED",
    ).count()
    last_run = db.query(ExtractionRun).filter(ExtractionRun.document_id == document.id).order_by(ExtractionRun.id.desc()).first()
    return {
        "id": document.id,
        "filename": document.filename,
        "doc_type": document.doc_type,
        "doc_date": document.doc_date.isoformat() if document.doc_date else None,
        "institution": institution.name if institution else None,
        "sha256": document.sha256,
        "source": document.source,
        "pages": len(json.loads(document.pages_json)),
        "pending_candidates": pending,
        "accepted_candidates": accepted,
        "last_run": {
            "id": last_run.id,
            "provider": last_run.provider,
            "candidates_total": last_run.candidates_total,
            "candidates_discarded": last_run.candidates_discarded,
            "latency_ms": last_run.latency_ms,
        } if last_run else None,
    }


@app.get("/api/v1/documents")
def list_documents(db: DbSession, user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN", "SENIOR_MANAGEMENT", "AUDITOR"))]) -> list[dict[str, Any]]:
    return [serialize_document(db, item) for item in db.query(Document).order_by(Document.id.desc()).all()]


@app.get("/api/v1/documents/{document_id}")
def get_document(document_id: int, db: DbSession, user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN", "SENIOR_MANAGEMENT", "AUDITOR"))]) -> dict[str, Any]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Document not found", "details": {}})
    payload = serialize_document(db, document)
    payload["page_text"] = json.loads(document.pages_json)
    return payload


@app.post("/api/v1/documents")
def upload_document(
    payload: DocumentUploadRequest,
    db: DbSession,
    user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN"))],
    request: Request,
) -> dict[str, Any]:
    pages = [block.strip() for block in payload.text.split("\f") if block.strip()] or [payload.text.strip()]
    doc_date: date | None = None
    if payload.doc_date:
        try:
            doc_date = date.fromisoformat(payload.doc_date)
        except ValueError:
            raise HTTPException(status_code=422, detail={"code": "INVALID_DATE", "message": "doc_date must be ISO format (YYYY-MM-DD)", "details": {}})
    institution_id = payload.institution_id
    if institution_id is None:
        institution = db.query(Institution).order_by(Institution.id).first()
        institution_id = institution.id if institution else None
    document = Document(
        institution_id=institution_id,
        application_id=None,
        filename=payload.filename,
        doc_type=payload.doc_type,
        doc_date=doc_date,
        sha256=compute_sha256(pages),
        pages_json=json.dumps(pages),
        source="uploaded",
        uploaded_by=user.id,
        created_at=Clock.now(),
    )
    db.add(document)
    db.flush()
    append_event(db, user.id, "DOCUMENT_UPLOADED", "document", str(document.id), after={"filename": document.filename, "doc_type": document.doc_type}, request_id=request.state.request_id)
    db.commit()
    db.refresh(document)
    return serialize_document(db, document)


@app.post("/api/v1/documents/{document_id}/extract")
def extract_document(
    document_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN"))],
    request: Request,
) -> dict[str, Any]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Document not found", "details": {}})
    run = run_extraction(db, document, user, request.state.request_id)
    candidates = db.query(ObligationCandidate).filter(
        ObligationCandidate.run_id == run.id,
    ).order_by(ObligationCandidate.source_page, ObligationCandidate.id).all()
    return {
        "run": {
            "id": run.id,
            "provider": run.provider,
            "model": run.model,
            "candidates_total": run.candidates_total,
            "candidates_grounded": run.candidates_grounded,
            "candidates_discarded": run.candidates_discarded,
            "latency_ms": run.latency_ms,
        },
        "candidates": [serialize_candidate(item) for item in candidates],
    }


@app.get("/api/v1/documents/{document_id}/candidates")
def list_candidates(document_id: int, db: DbSession, user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN", "SENIOR_MANAGEMENT", "AUDITOR"))]) -> list[dict[str, Any]]:
    candidates = db.query(ObligationCandidate).filter(ObligationCandidate.document_id == document_id).order_by(ObligationCandidate.source_page, ObligationCandidate.id).all()
    return [serialize_candidate(item) for item in candidates]


@app.post("/api/v1/candidates/{candidate_id}/accept")
def accept_obligation(
    candidate_id: int,
    payload: CandidateDecisionRequest,
    db: DbSession,
    user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN"))],
    request: Request,
) -> dict[str, Any]:
    candidate = db.get(ObligationCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Candidate not found", "details": {}})
    try:
        created = accept_candidate(db, candidate, user, request.state.request_id, {"description": payload.description, "due_date": payload.due_date})
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "CANDIDATE_CONFLICT", "message": str(exc), "details": {}})
    db.refresh(candidate)
    return {"candidate": serialize_candidate(candidate), "undertaking_id": created.id if created else None}


@app.post("/api/v1/candidates/{candidate_id}/reject")
def reject_obligation(
    candidate_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require("COMPLIANCE_OFFICER", "SYSTEM_ADMIN"))],
    request: Request,
) -> dict[str, Any]:
    candidate = db.get(ObligationCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Candidate not found", "details": {}})
    reject_candidate(db, candidate, user, request.state.request_id)
    db.refresh(candidate)
    return {"candidate": serialize_candidate(candidate)}


@app.get("/api/v1/admin/rules")
def rules(db: DbSession, _: Annotated[User, Depends(require("SYSTEM_ADMIN", "AUDITOR", "SENIOR_MANAGEMENT"))]) -> list[dict[str, Any]]:
    return [{"key": row.key, "value": json.loads(row.value_json), "tag": row.tag, "version": row.version} for row in db.query(AppConfig).order_by(AppConfig.key)]


@app.post("/api/v1/simulations")
def simulate(
    payload: SimulationRequest,
    user: Annotated[User, Depends(require("SENIOR_MANAGEMENT", "SYSTEM_ADMIN"))],
) -> dict[str, Any]:
    try:
        result = run_simulation(
            additional_scrutiny_officers=payload.additional_scrutiny_officers,
            arrival_multiplier=payload.arrival_multiplier,
            service_multiplier=payload.service_multiplier,
            replications=payload.replications,
            days=payload.working_days,
            seed=payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_SCENARIO", "message": str(exc), "details": {}})
    return result


@app.get("/api/v1/inbox")
def inbox(db: DbSession, user: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    query = db.query(Application).filter(Application.stage != "DONE")
    if user.role == "INSTITUTION_APPLICANT":
        query = query.filter(Application.institution_id == user.institution_id)
    elif user.region_code and user.role in {"SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_OFFICER"}:
        query = query.filter(Application.region_code == user.region_code)
    items = []
    for item in query.all():
        age = max(0, (Clock.now() - item.created_at).days)
        sla_pressure = min(1.0, age / 20)
        evc_ready = 1.0 if item.stage == "EVC" else 0.0
        factors = {"sla_pressure": round(sla_pressure, 2), "escalation_level": 0.0, "obligation_urgency": 0.0, "evc_readiness": evc_ready, "case_age": min(1.0, age / 60), "blocking_others": 0.0}
        score = sum(factors[key] * weight for key, weight in {"sla_pressure": .35, "escalation_level": .2, "obligation_urgency": .15, "evc_readiness": .1, "case_age": .1, "blocking_others": .1}.items())
        items.append({"application": serialize_application(db, item), "score": round(score, 4), "factors": factors})
    return sorted(items, key=lambda value: (-value["score"], value["application"]["created_at"], value["application"]["reference_no"]))[:100]


def serialize_letter(letter: Letter) -> dict[str, Any]:
    return {
        "id": letter.id,
        "reference_no": letter.reference_no,
        "letter_type": letter.letter_type,
        "verify_token": letter.verify_token,
        "sha256": letter.sha256,
        "status": letter.status,
        "issued_at": letter.issued_at.isoformat(),
        "verify_url": f"{settings.public_base_url}/verify/{letter.verify_token}",
        "download_url": f"/api/v1/letters/{letter.id}/pdf",
    }


@app.get("/api/v1/letters")
def list_letters(db: DbSession, _: Annotated[User, Depends(current_user)]) -> list[dict[str, Any]]:
    return [serialize_letter(letter) for letter in db.query(Letter).order_by(Letter.id.desc()).limit(100).all()]


@app.post("/api/v1/letters")
def create_letter(
    payload: LetterRequest,
    db: DbSession,
    user: Annotated[User, Depends(require("SCRUTINY_OFFICER", "EVC_COORDINATOR", "SYSTEM_ADMIN"))],
    request: Request,
) -> dict[str, Any]:
    application = db.get(Application, payload.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Application not found", "details": {}})
    default_body = {
        "deficiency_notice": [
            "The following deficiency has been observed in your application and requires a response:",
            "",
            payload.body or "Provide the current registered campus document within the configured response period.",
            "",
            "You may respond through the FlowWise portal. This notice switches the SLA holder to the institution.",
        ],
        "evc_schedule": [
            "An Expert Visit Committee has been scheduled for your institution.",
            "",
            payload.body or "The visit details and panel are recorded in the FlowWise portal.",
        ],
        "confirmation_letter": [
            "This letter confirms the recorded outcome for your application.",
            "",
            payload.body or "Please refer to the FlowWise portal for the full case timeline.",
        ],
    }
    body_lines = default_body.get(payload.letter_type, [payload.body or "Please refer to the FlowWise portal."])
    letter = generate_letter(db, user, application, payload.letter_type, body_lines, request.state.request_id)
    return serialize_letter(letter)


@app.get("/api/v1/letters/{letter_id}/pdf")
def download_letter(letter_id: int, db: DbSession, _: Annotated[User, Depends(current_user)]) -> FileResponse:
    letter = db.get(Letter, letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Letter not found", "details": {}})
    return FileResponse(letter.file_path, media_type="application/pdf", filename=f"{letter.reference_no}.pdf")


@app.get("/api/v1/verify/{token}")
def public_verify(token: str, db: DbSession) -> dict[str, Any]:
    """Public verification endpoint — no authentication, no sensitive content."""
    result = verify_letter(db, token)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail={"code": "LETTER_NOT_FOUND", "message": "No letter matches this verification code", "details": {}})
    return result


@app.post("/api/v1/verify/{token}/match")
def public_verify_match(token: str, db: DbSession) -> dict[str, Any]:
    letter = db.query(Letter).filter(Letter.verify_token == token).first()
    if letter is None:
        raise HTTPException(status_code=404, detail={"code": "LETTER_NOT_FOUND", "message": "No letter matches this verification code", "details": {}})
    try:
        file_bytes = open(letter.file_path, "rb").read()
    except OSError:
        raise HTTPException(status_code=404, detail={"code": "FILE_MISSING", "message": "The stored file is unavailable", "details": {}})
    uploaded_hash = hashlib.sha256(file_bytes).hexdigest()
    return verify_letter(db, token, uploaded_hash)


@app.get("/api/v1/audit/events")
def audit_events(db: DbSession, _: Annotated[User, Depends(require("AUDITOR", "SYSTEM_ADMIN", "SENIOR_MANAGEMENT"))]) -> list[dict[str, Any]]:
    return [{"id": event.id, "action": event.action, "entity_type": event.entity_type, "entity_id": event.entity_id, "occurred_at": event.occurred_at.isoformat(), "reason": event.reason, "hash": event.hash, "prev_hash": event.prev_hash} for event in db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(200)]


@app.get("/api/v1/audit/verify")
def audit_verify(db: DbSession, _: Annotated[User, Depends(require("AUDITOR", "SYSTEM_ADMIN"))]) -> dict[str, Any]:
    return verify_chain(db)


@app.get("/api/v1/demo/clock")
def demo_clock(_: Annotated[User, Depends(require("SYSTEM_ADMIN"))]) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Demo controls are disabled", "details": {}})
    return {"now": Clock.now().isoformat(), "offset_seconds": Clock._offset_seconds, "demo_mode": settings.demo_mode}


@app.post("/api/v1/demo/clock/advance")
def advance_clock(payload: ClockAdvanceRequest, user: Annotated[User, Depends(require("SYSTEM_ADMIN"))], db: DbSession) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Demo controls are disabled", "details": {}})
    seconds = int(payload.working_hours * 3600 + payload.days * 86400)
    now = Clock.advance(seconds)
    config = db.get(AppConfig, "demo_clock_offset_seconds")
    if config:
        config.value_json = str(Clock._offset_seconds)
    append_event(db, user.id, "DEMO_CLOCK_ADVANCED", "demo_clock", "clock", after={"offset_seconds": Clock._offset_seconds})
    db.commit()
    return {"now": now.isoformat(), "offset_seconds": Clock._offset_seconds}


@app.post("/api/v1/demo/tamper")
def demo_tamper(user: Annotated[User, Depends(require("SYSTEM_ADMIN"))], db: DbSession) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Demo controls are disabled", "details": {}})
    try:
        event_id = tamper_first_event(db)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "NO_AUDIT_EVENTS", "message": str(exc), "details": {}})
    return {"tampered_event_id": event_id, "label": "DEMO ONLY"}


@app.post("/api/v1/demo/reset")
def demo_reset(user: Annotated[User, Depends(require("SYSTEM_ADMIN"))], db: DbSession) -> dict[str, str]:
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Demo controls are disabled", "details": {}})
    seed_database(db)
    return {"status": "reset", "message": "Synthetic demo data restored"}


def initialize_seed() -> None:
    db = SessionLocal()
    try:
        if db.query(func.count(User.id)).scalar() == 0:
            seed_database(db)
        else:
            offset = db.get(AppConfig, "demo_clock_offset_seconds")
            if offset:
                Clock.set_offset(int(json.loads(offset.value_json)))
    finally:
        db.close()


initialize_seed()
