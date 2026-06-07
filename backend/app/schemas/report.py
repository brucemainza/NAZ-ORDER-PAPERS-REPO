from datetime import date
from uuid import UUID

from pydantic import BaseModel


class SessionSubmissionReport(BaseModel):
    session_id: UUID
    session_code: str
    session_name: str
    total: int
    questions: int
    motions: int
    pending_review: int
    duplicates: int


class MatchRateReport(BaseModel):
    period: date
    total_reviews: int
    duplicate_or_similar: int
    match_rate: float


class ActivityReport(BaseModel):
    name: str
    department: str | None
    submissions: int
    pending_review: int
    duplicates: int


class ReportsResponse(BaseModel):
    submissions_by_session: list[SessionSubmissionReport]
    similarity_match_rate: list[MatchRateReport]
    member_activity: list[ActivityReport]
    department_activity: list[ActivityReport]
