from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_validator,
    model_validator,
)


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