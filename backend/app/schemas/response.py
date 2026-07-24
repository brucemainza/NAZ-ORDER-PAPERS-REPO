from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionResponseCreate(BaseModel):
    response_text: str = Field(min_length=1)
    response_date: date

    @field_validator("response_text", mode="before")
    @classmethod
    def strip_response_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class QuestionResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    response_text: str
    response_date: date
    recorded_by: UUID
    status: str
    created_at: datetime
