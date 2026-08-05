from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.ai.interfaces import LexicalRetriever
from app.ai.schemas import RecordMatch, SimilaritySearchRequest
from app.models import ParliamentaryRecord
from app.retrieval.bm25 import rank_records
from app.services.record_visibility import (
    restrict_archive_visibility,
    restrict_draft_visibility,
)


class BM25LexicalRetriever(LexicalRetriever):
    """Lexical retriever that applies SQL filters then runs in-process BM25.

    For the prototype this is acceptable because the SQL filters (session,
    item_type, status) narrow the candidate set dramatically. When the corpus
    grows beyond comfortable in-process ranking, this should be replaced by a
    PostgreSQL tsvector/GIN full-text index path.
    """

    def __init__(self, db: Session, user) -> None:
        self._db = db
        self._user = user

    def search(
        self,
        request: SimilaritySearchRequest,
        k: int,
    ) -> list[RecordMatch]:
        query = self._base_query()
        query = self._apply_filters(query, request)
        # Limit the in-process BM25 window to keep latency low.
        candidates = list(self._db.execute(query.limit(200)).scalars().all())
        if not candidates:
            return []

        matches = rank_records(request.query_text, candidates, k)
        return [
            RecordMatch(
                record_id=UUID(match.record.id),
                score=min(1.0, match.score / 100.0),
                lexical_rank=rank,
                metadata={
                    "subject": match.record.subject,
                    "member": match.record.member,
                    "ministry": match.record.ministry,
                    "matched_terms": match.matched_terms,
                },
            )
            for rank, match in enumerate(matches, start=1)
        ]

    def _base_query(self):
        return (
            select(ParliamentaryRecord)
            .options(joinedload(ParliamentaryRecord.session))
            .order_by(ParliamentaryRecord.created_at.desc())
        )

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
        if request.exclude_ids:
            query = query.where(
                ParliamentaryRecord.id.not_in(tuple(request.exclude_ids))
            )

        # Basic keyword prefilter to avoid loading the whole table.
        search_term = request.query_text.strip()
        if len(search_term) >= 3:
            pattern = f"%{search_term}%"
            query = query.where(
                or_(
                    ParliamentaryRecord.subject.ilike(pattern),
                    ParliamentaryRecord.full_text.ilike(pattern),
                    ParliamentaryRecord.member.ilike(pattern),
                    ParliamentaryRecord.ministry.ilike(pattern),
                )
            )

        return query
