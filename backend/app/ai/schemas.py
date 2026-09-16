import datetime as dt
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SimilaritySearchRequest(BaseModel):
    """Input for the hybrid similarity search pipeline."""

    query_text: str = Field(..., min_length=1)
    session_id: UUID | None = None
    item_type: str | None = None
    status: str | None = None
    date: dt.date | None = None
    member: str | None = None
    ministry: str | None = None
    exclude_ids: list[UUID] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class RecordMatch(BaseModel):
    """A single retrieved candidate with per-retriever rank information."""

    record_id: UUID
    score: float = Field(..., ge=0.0, le=1.0)
    ranking_score: float | None = Field(default=None, ge=0.0, le=1.0)
    cosine_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    lexical_score: float | None = Field(default=None, ge=0.0)
    lexical_rank: int | None = None
    semantic_rank: int | None = None
    rrf_score: float | None = None
    metadata: dict = Field(default_factory=dict)


class SimilaritySearchResponse(BaseModel):
    """Output of the hybrid similarity search pipeline."""

    query_text: str
    results: list[RecordMatch]
    embedding_model: str
    total_lexical: int
    total_semantic: int
    retrieval_mode: str = "hybrid"
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class AIReviewSubmission(BaseModel):
    """Human reviewer feedback on an AI suggestion."""

    record_id: UUID
    similar_record_id: UUID | None = None
    decision: Literal["Clear (New)", "Duplicate", "Substantially Similar"]
    notes: str | None = None

    @model_validator(mode="after")
    def validate_related_record(self):
        needs_related_record = self.decision in {
            "Duplicate",
            "Substantially Similar",
        }
        if needs_related_record and self.similar_record_id is None:
            raise ValueError(
                "A related record is required for duplicate or similar decisions"
            )
        if not needs_related_record and self.similar_record_id is not None:
            raise ValueError("Clear decisions cannot reference a related record")
        if self.similar_record_id == self.record_id:
            raise ValueError("A record cannot be marked similar to itself")
        return self


class AIHealthResponse(BaseModel):
    """Health status of the AI layer."""

    ollama_reachable: bool
    embedding_model_loaded: bool
    embedding_dimension: int
    embedding_model: str
