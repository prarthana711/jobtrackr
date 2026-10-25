from datetime import date, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from app.models import ApplicationStatus
from app.services.workflow import allowed_next as workflow_allowed_next

# ---------- Auth ----------


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long (max 72 bytes)")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Jobs ----------


def validate_url(value: str) -> str | None:
    if value == "":
        return None
    if not value.lower().startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return value


# Reusable field types: each one strips spaces and enforces a length
RequiredText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)
]
Url = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=500),
    AfterValidator(validate_url),
]


class JobCreate(BaseModel):
    title: RequiredText
    company: RequiredText
    location: OptionalText | None = None
    url: Url | None = None
    description: Description


class JobUpdate(BaseModel):
    """Every field is optional: PATCH changes only what the client sends."""

    title: RequiredText | None = None
    company: RequiredText | None = None
    location: OptionalText | None = None
    url: Url | None = None
    description: Description | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self):
        # Sending {"title": null} is different from not sending title at all
        for name in ("title", "company", "description"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str | None
    url: str | None
    description: str
    created_at: datetime


class JobList(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int
    pages: int

# ---------- Applications ----------

Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class ApplicationCreate(BaseModel):
    job_id: int
    notes: Notes | None = None


class ApplicationUpdate(BaseModel):
    """Notes and applied date only. Status changes have their own endpoint."""

    notes: Notes | None = None
    applied_on: date | None = None


class StatusChange(BaseModel):
    status: ApplicationStatus


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str | None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    status: ApplicationStatus
    applied_on: date | None
    notes: str | None
    created_at: datetime
    job: JobSummary

    @computed_field
    @property
    def allowed_next(self) -> list[ApplicationStatus]:
        """Tells the frontend which buttons to show."""
        return workflow_allowed_next(self.status)


class ApplicationList(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int
    page_size: int
    pages: int


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: str | None
    to_status: str
    changed_at: datetime

# ---------- Resumes ----------


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    size_bytes: int
    parsed_skills: list[str]
    uploaded_at: datetime


class ResumeDetail(ResumeOut):
    raw_text: str

# ---------- Matching ----------


class MatchRequest(BaseModel):
    resume_id: int
    job_id: int


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    job_id: int
    score: float
    skill_score: float | None
    text_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    computed_at: datetime
    job: JobSummary

# ---------- Analytics ----------


class FunnelStage(BaseModel):
    stage: ApplicationStatus
    count: int
    percent_of_total: float


class FunnelOut(BaseModel):
    total: int
    stages: list[FunnelStage]
    rejected: int
    response_rate: float | None
    current: dict[str, int]


class WeekCount(BaseModel):
    week_start: date
    applications: int


class WeakSpot(BaseModel):
    skill: str
    missing_in_jobs: int
    percent_of_jobs: float


class WeakSpotsOut(BaseModel):
    jobs_analysed: int
    skills: list[WeakSpot]