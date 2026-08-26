from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewDecisionCreate(BaseModel):
    similar_record_id: UUID | None = None
    decision: str = Field(pattern="^(Clear \\(New\\)|Duplicate|Substantially Similar)$")
    notes: str | None = None

    @model_validator(mode="after")
    def validate_related_record(self):
        needs_related_record = self.decision in {
            "Duplicate",
            "Substantially Similar",
        }
        if needs_related_record and self.similar_record_id is None:
            raise ValueError(
                "A related record is required for duplicate or similar decisions"
            )
        if not needs_related_record and self.similar_record_id is not None:
            raise ValueError("Clear decisions cannot reference a related record")
        return self


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


class WorkflowReviewCreate(BaseModel):
    action: Literal["Approve", "Reject", "Request Changes"]
    notes: str | None = None


class WorkflowReviewOut(BaseModel):
    id: UUID
    record_id: UUID
    action: str
    status: str
    reviewer_id: UUID
    reviewer_name: str
    notes: str | None
    created_at: datetime
