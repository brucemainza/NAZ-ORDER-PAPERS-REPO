import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    query_text: str = Field(min_length=3)
    session_id: UUID | None = None
    item_type: str | None = None
    status: str | None = None
    date: dt.date | None = None
    member: str | None = None
    ministry: str | None = None
    mode: str = Field(default="hybrid", pattern="^(keyword|hybrid)$")
    limit: int = Field(default=5, ge=1, le=20)
    offset: int = Field(default=0, ge=0)


class SearchRecordOut(BaseModel):
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
    sitting_date: dt.date | None
    created_at: dt.datetime


class SearchResultOut(BaseModel):
    rank: int
    score: float
    matched_terms: list[str]
    record: SearchRecordOut


class SearchResponse(BaseModel):
    query_text: str
    total_candidates: int
    total_results: int
    results: list[SearchResultOut]
