from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord
from app.similarity.base import SimilarityBackend, SimilarityMatch
from app.similarity.embeddings import EmbeddingGenerator


class PgVectorSimilarityBackend(SimilarityBackend):
    """PostgreSQL cosine-similarity adapter backed by pgvector."""

    def __init__(
        self,
        db: Session,
        embedding_generator: EmbeddingGenerator,
    ) -> None:
        self._db = db
        self._embedding_generator = embedding_generator

    def find_similar(
        self,
        text: str,
        threshold: float,
        top_n: int,
        *,
        exclude_ids: Collection[UUID] = (),
        statuses: Collection[str] | None = None,
        item_type: str | None = None,
    ) -> list[SimilarityMatch]:
        if not 0 <= threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        if top_n < 1:
            raise ValueError("top_n must be positive")
        if not text.strip():
            return []

        query_embedding = self._embedding_generator.embed(text)
        if not any(query_embedding):
            return []

        distance = ParliamentaryRecord.embedding.cosine_distance(query_embedding)
        query = (
            select(
                ParliamentaryRecord.id,
                distance.label("cosine_distance"),
            )
            .where(ParliamentaryRecord.embedding.is_not(None))
            .where(distance <= 1 - threshold)
        )

        excluded = tuple(exclude_ids)
        if excluded:
            query = query.where(ParliamentaryRecord.id.not_in(excluded))
        if statuses is not None:
            normalized_statuses = tuple(statuses)
            if not normalized_statuses:
                return []
            query = query.where(ParliamentaryRecord.status.in_(normalized_statuses))
        if item_type is not None:
            query = query.where(ParliamentaryRecord.item_type == item_type)

        rows = self._db.execute(
            query.order_by(distance.asc(), ParliamentaryRecord.id.asc()).limit(top_n)
        ).all()

        return [
            SimilarityMatch(
                source_id=row.id,
                score=round(max(0.0, min(1.0, 1.0 - float(row.cosine_distance))), 6),
            )
            for row in rows
        ]
