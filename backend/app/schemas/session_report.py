from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionReportSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    start_date: date
    end_date: date
    status: str


class SessionReportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    questions: int
    motions: int


class SessionReportItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    member: str
    ministry: str | None
    subject: str
    full_text: str
    status: str
    sitting_date: date | None
    created_at: datetime


class SessionReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session: SessionReportSessionOut
    summary: SessionReportSummaryOut
    items: list[SessionReportItemOut]
