from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field, field_validator

IDEMPOTENCY_KEY_MAX_LENGTH = 128


class JobCreateRequest(BaseModel):
    type: str = Field(..., min_length=1, max_length=100, examples=["send_email"])
    payload: Dict[str, Any] = Field(default_factory=dict, examples=[{"to": "user@example.com"}])
    idempotency_key: str | None = Field(default=None)

    @field_validator("type")
    @classmethod
    def clean_type(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("type cannot be blank")
        return cleaned

    @field_validator("idempotency_key")
    @classmethod
    def clean_key(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("idempotency_key cannot be blank")
        if len(cleaned) > IDEMPOTENCY_KEY_MAX_LENGTH:
            raise ValueError(
                f"idempotency_key exceeds max length {IDEMPOTENCY_KEY_MAX_LENGTH}"
            )
        return cleaned


class JobCreateResponse(BaseModel):
    job_id: int
    status: str

JobCreate = JobCreateRequest

class JobStatusResponse(BaseModel):
    id: int
    type: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True