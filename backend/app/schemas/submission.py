from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.search import SearchResultOut


class SubmissionCreate(BaseModel):
    item_type: str = Field(pattern="^(Question|Motion)$")
    session_id: UUID
    member: str = Field(min_length=3, max_length=255)
    ministry: str | None = Field(default=None, max_length=255)
    answer_type: Literal["Oral", "Written"] | None = None
    subject: str = Field(min_length=5, max_length=500)
    full_text: str = Field(min_length=40)

    @field_validator("member", "ministry", "subject", "full_text", mode="before")
    @classmethod
    def strip_text_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_question_ministry(self):
        if self.item_type == "Question" and not (self.ministry or "").strip():
            raise ValueError("Ministry or department is required for questions")
        if self.item_type == "Question" and self.answer_type is None:
            raise ValueError("Oral or written answer type is required for questions")
        if self.item_type == "Motion" and self.answer_type is not None:
            raise ValueError("Answer type only applies to questions")
        return self


class SubmissionDraftUpdate(BaseModel):
    member: str | None = Field(default=None, min_length=3, max_length=255)
    ministry: str | None = Field(default=None, max_length=255)
    answer_type: Literal["Oral", "Written"] | None = None
    subject: str | None = Field(default=None, min_length=5, max_length=500)
    full_text: str | None = Field(default=None, min_length=40)

    @field_validator("member", "ministry", "subject", "full_text", mode="before")
    @classmethod
    def strip_text_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one draft field must be provided")
        return self


class SubmissionSchedule(BaseModel):
    sitting_date: date


class SubmissionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    session_id: UUID
    member: str
    ministry: str | None
    answer_type: str | None
    subject: str
    full_text: str
    status: str
    submitted_by: UUID | None
    sitting_date: date | None
    created_at: datetime


class SubmissionResponse(BaseModel):
    record: SubmissionRecordOut
    candidates: list[SearchResultOut]
