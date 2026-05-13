from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    query_text: str = Field(min_length=3)
    session_id: UUID | None = None
    item_type: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    session_id: UUID
    member: str
    ministry: str | None
    subject: str
    full_text: str
    status: str
    created_at: datetime


class SearchResultOut(BaseModel):
    rank: int
    score: float
    matched_terms: list[str]
    record: SearchRecordOut


class SearchResponse(BaseModel):
    query_text: str
    total_candidates: int
    results: list[SearchResultOut]
