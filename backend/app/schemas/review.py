from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewDecisionCreate(BaseModel):
    similar_record_id: UUID | None = None
    decision: str = Field(pattern="^(Clear \\(New\\)|Duplicate|Substantially Similar)$")
    notes: str | None = None


class ReviewDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    similar_record_id: UUID | None
    decision: str
    is_duplicate: bool
    reviewer_id: UUID
    reviewer_name: str | None = None
    notes: str | None
    created_at: datetime
