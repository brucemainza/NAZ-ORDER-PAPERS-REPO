from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SimilarityCheckRequest(BaseModel):
    item_type: Literal["Question", "Motion"]
    session_id: UUID | None = None
    subject: str = Field(min_length=5, max_length=500)
    full_text: str = Field(min_length=40)

    @field_validator("subject", "full_text", mode="before")
    @classmethod
    def strip_text_fields(cls, value):
        return value.strip() if isinstance(value, str) else value


class SimilarityMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    score: float
    match_type: str
    session: str
    date: date
    member_name: str
    source_record: UUID
    source_id: UUID


class SimilarityCheckResponse(BaseModel):
    possible_duplicate: bool
    threshold: float
    matches: list[SimilarityMatchOut]
    previously_addressed: list[SimilarityMatchOut] = Field(default_factory=list)
