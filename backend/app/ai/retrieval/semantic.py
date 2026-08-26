from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.interfaces import SemanticRetriever
from app.ai.schemas import RecordMatch, SimilaritySearchRequest
from app.models import ParliamentaryRecord, RecordChunk
from app.services.record_visibility import (
    restrict_archive_visibility,
    restrict_draft_visibility,
)


class PgVectorSemanticRetriever(SemanticRetriever):
    """Retrieve compatible chunks and collapse the best passage per record."""

    def __init__(
        self,
        db: Session,
        user,
        *,
        model: str,
        model_digest: str,
        dimension: int,
        preprocessing_version: str,
    ) -> None:
        self._db = db
        self._user = user
        self._model = model
        self._model_digest = model_digest
        self._dimension = dimension
        self._preprocessing_version = preprocessing_version

    def search(
        self,
        request: SimilaritySearchRequest,
        query_embedding: list[float],
        k: int,
    ) -> list[RecordMatch]:
        if len(query_embedding) != self._dimension:
            raise RuntimeError(
                f"embedding dimension mismatch: expected {self._dimension}, "
                f"got {len(query_embedding)}"
            )
        distance = RecordChunk.embedding.cosine_distance(query_embedding)
        candidates = (
            select(
                RecordChunk.record_id.label("record_id"),
                RecordChunk.chunk_index.label("chunk_index"),
                RecordChunk.chunk_text.label("chunk_text"),
                distance.label("cosine_distance"),
            )
            .join(
                ParliamentaryRecord,
                ParliamentaryRecord.id == RecordChunk.record_id,
            )
            .where(
                RecordChunk.embedding.is_not(None),
                RecordChunk.embedding_model == self._model,
                RecordChunk.model_digest == self._model_digest,
                RecordChunk.dimension == self._dimension,
                RecordChunk.preprocessing_version == self._preprocessing_version,
            )
        )
        candidates = self._apply_filters(candidates, request)
        best_chunks = (
            candidates.distinct(RecordChunk.record_id)
            .order_by(
                RecordChunk.record_id,
                distance.asc(),
                RecordChunk.chunk_index.asc(),
            )
            .subquery()
        )
        rows = self._db.execute(
            select(
                ParliamentaryRecord,
                best_chunks.c.chunk_index,
                best_chunks.c.chunk_text,
                best_chunks.c.cosine_distance,
            )
            .join(best_chunks, best_chunks.c.record_id == ParliamentaryRecord.id)
            .order_by(
                best_chunks.c.cosine_distance.asc(),
                ParliamentaryRecord.id.asc(),
            )
            .limit(k)
        ).all()
        return [
            RecordMatch(
                record_id=row.ParliamentaryRecord.id,
                score=round(
                    max(0.0, min(1.0, 1.0 - float(row.cosine_distance))), 6
                ),
                ranking_score=round(
                    max(0.0, min(1.0, 1.0 - float(row.cosine_distance))), 6
                ),
                cosine_similarity=round(
                    max(0.0, min(1.0, 1.0 - float(row.cosine_distance))), 6
                ),
                semantic_rank=rank,
                metadata={
                    "subject": row.ParliamentaryRecord.subject,
                    "member": row.ParliamentaryRecord.member,
                    "ministry": row.ParliamentaryRecord.ministry,
                    "chunk_index": row.chunk_index,
                    "chunk_excerpt": row.chunk_text[:500],
                    "model_digest": self._model_digest,
                    "preprocessing_version": self._preprocessing_version,
                },
            )
            for rank, row in enumerate(rows, start=1)
        ]

    def _apply_filters(self, query, request: SimilaritySearchRequest):
        query = restrict_draft_visibility(query, self._user)
        query = restrict_archive_visibility(query, self._user, "search_archive")
        if request.session_id:
            query = query.where(ParliamentaryRecord.session_id == request.session_id)
        if request.item_type:
            query = query.where(
                func.lower(ParliamentaryRecord.item_type)
                == request.item_type.strip().lower()
            )
        if request.status:
            query = query.where(
                func.lower(ParliamentaryRecord.status)
                == request.status.strip().lower()
            )
        if request.date:
            query = query.where(
                func.date(ParliamentaryRecord.created_at) == request.date
            )
        if request.member:
            query = query.where(
                ParliamentaryRecord.member.ilike(f"%{request.member.strip()}%")
            )
        if request.ministry:
            query = query.where(
                ParliamentaryRecord.ministry.ilike(f"%{request.ministry.strip()}%")
            )
        if request.exclude_ids:
            query = query.where(
                ParliamentaryRecord.id.not_in(tuple(request.exclude_ids))
            )
        return query
