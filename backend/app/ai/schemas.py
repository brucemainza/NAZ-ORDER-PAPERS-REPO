import datetime as dt
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field


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


class AIExplainRequest(BaseModel):
    """Input for the grounded explanation endpoint."""

    query_text: str = Field(..., min_length=1)
    record_ids: list[UUID] = Field(..., min_length=1, max_length=5)


class AIExplanation(BaseModel):
    """Structured explanation produced by the local LLM."""

    classification: str = Field(
        ...,
        pattern="^(exact_duplicate|potential_duplicate|related_matter|no_strong_match)$",
    )
    confidence: str = Field(..., pattern="^(low|medium|high)$")
    summary: str
    shared_points: list[str] = Field(default_factory=list)
    important_differences: list[str] = Field(default_factory=list)
    supporting_record_ids: list[UUID] = Field(default_factory=list)
    human_review_required: bool = True
    model: str
    error: str | None = None


class AIReviewSubmission(BaseModel):
    """Human reviewer feedback on an AI suggestion."""

    record_id: UUID
    similar_record_id: UUID | None = None
    decision: Literal["Clear (New)", "Duplicate", "Substantially Similar"]
    notes: str | None = None


class AIHealthResponse(BaseModel):
    """Health status of the AI layer."""

    ollama_reachable: bool
    embedding_model_loaded: bool
    llm_model_loaded: bool
    embedding_dimension: int
    embedding_model: str
    llm_model: str
