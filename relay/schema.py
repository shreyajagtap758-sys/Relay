from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field

class JobCreateRequest(BaseModel):
    type: str = Field(..., min_length=1, max_length=100, examples=["send_email"])
    payload: Dict[str, Any] = Field(default_factory=dict, examples=[{"to": "user@example.com"}])

class JobCreateResponse(BaseModel):
    job_id: int
    status: str

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