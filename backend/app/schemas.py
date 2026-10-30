from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TransitionRequest(BaseModel):
    event: str
    reason: str | None = None
    expected_version: int = Field(ge=1)


class ObservationRequest(BaseModel):
    category: str
    remarks: str = Field(min_length=3, max_length=2000)


class ResponseRequest(BaseModel):
    observation_id: int
    text: str = Field(min_length=3, max_length=4000)


class ClockAdvanceRequest(BaseModel):
    working_hours: float = Field(default=0, ge=0, le=1000)
    days: float = Field(default=0, ge=0, le=365)


class DocumentUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    doc_type: str = Field(default="approval_letter", max_length=40)
    doc_date: str | None = None
    institution_id: int | None = None
    text: str = Field(min_length=10, max_length=50000)


class CandidateDecisionRequest(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    due_date: str | None = None


class WorkflowDraftRequest(BaseModel):
    template_code: str = Field(min_length=2, max_length=40)
    graph: dict = Field(default_factory=dict)


class WorkflowValidateRequest(BaseModel):
    graph: dict


class WorkflowRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class LetterRequest(BaseModel):
    application_id: int
    letter_type: str = Field(default="deficiency_notice", max_length=40)
    body: str = Field(default="", max_length=4000)


class SimulationRequest(BaseModel):
    additional_scrutiny_officers: dict[str, int] = Field(default_factory=dict)
    arrival_multiplier: float = Field(default=1.0, ge=0.1, le=5)
    service_multiplier: float = Field(default=1.0, ge=0.1, le=5)
    replications: int = Field(default=30, ge=1, le=100)
    working_days: int = Field(default=120, ge=1, le=365)
    seed: int = Field(default=42, ge=0)
