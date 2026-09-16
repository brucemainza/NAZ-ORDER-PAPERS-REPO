from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SessionStatus = Literal["Active", "Closed", "Upcoming"]


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    start_date: date
    end_date: date
    status: str


class SessionUpdate(BaseModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: SessionStatus | None = None


class SessionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1)
    start_date: date
    end_date: date
    status: SessionStatus = "Upcoming"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self
