from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
