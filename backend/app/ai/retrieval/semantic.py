from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.ai.interfaces import SemanticRetriever
from app.ai.schemas import RecordMatch, SimilaritySearchRequest
from app.models import ParliamentaryRecord
from app.services.record_visibility import (
    restrict_archive_visibility,
    restrict_draft_visibility,
)


class PgVectorSemanticRetriever(SemanticRetriever):
    """Semantic retriever using pgvector cosine distance."""

    def __init__(self, db: Session, user) -> None:
        self._db = db
        self._user = user

    def search(
        self,
        request: SimilaritySearchRequest,
        query_embedding: list[float],
        k: int,
    ) -> list[RecordMatch]:
        distance = ParliamentaryRecord.embedding.cosine_distance(query_embedding)

        query = (
            select(ParliamentaryRecord, distance.label("cosine_distance"))
            .options(joinedload(ParliamentaryRecord.session))
            .where(ParliamentaryRecord.embedding.is_not(None))
        )
        query = self._apply_filters(query, request)

        rows = self._db.execute(
            query.order_by(distance.asc(), ParliamentaryRecord.id.asc()).limit(k)
        ).all()

        return [
            RecordMatch(
                record_id=row.ParliamentaryRecord.id,
                score=round(max(0.0, min(1.0, 1.0 - float(row.cosine_distance))), 6),
                semantic_rank=rank,
                metadata={
                    "subject": row.ParliamentaryRecord.subject,
                    "member": row.ParliamentaryRecord.member,
                    "ministry": row.ParliamentaryRecord.ministry,
                },
            )
            for rank, row in enumerate(rows, start=1)
        ]

    def _apply_filters(self, query, request: SimilaritySearchRequest):
        # Visibility filters need access to the ParliamentaryRecord entity.
        # The query already selects from that table, so restrict_* helpers work.
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
