from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.search import SearchResultOut


class SubmissionCreate(BaseModel):
    item_type: str = Field(pattern="^(Question|Motion)$")
    session_id: UUID
    member: str = Field(min_length=3, max_length=255)
    ministry: str | None = Field(default=None, max_length=255)
    answer_type: Literal["Oral", "Written"] | None = None
    subject: str = Field(min_length=5, max_length=500)
    full_text: str = Field(min_length=40)

    @model_validator(mode="after")
    def validate_question_ministry(self):
        if self.item_type == "Question" and not (self.ministry or "").strip():
            raise ValueError("Ministry or department is required for questions")
        if self.item_type == "Question" and self.answer_type is None:
            raise ValueError("Oral or written answer type is required for questions")
        if self.item_type == "Motion" and self.answer_type is not None:
            raise ValueError("Answer type only applies to questions")
        return self


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
    created_at: datetime


class SubmissionResponse(BaseModel):
    record: SubmissionRecordOut
    candidates: list[SearchResultOut]
