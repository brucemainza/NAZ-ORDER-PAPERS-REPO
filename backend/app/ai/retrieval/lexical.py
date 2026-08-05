import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.interfaces import LexicalRetriever
from app.ai.schemas import RecordMatch, SimilaritySearchRequest
from app.models import ParliamentaryRecord
from app.services.record_visibility import (
    restrict_archive_visibility,
    restrict_draft_visibility,
)

TERM_PATTERN = re.compile(r"[a-z0-9]+")


class PostgresLexicalRetriever(LexicalRetriever):
    """Rank and paginate weighted full-text matches entirely in PostgreSQL."""

    def __init__(self, db: Session, user) -> None:
        self._db = db
        self._user = user

    def search(
        self,
        request: SimilaritySearchRequest,
        k: int,
    ) -> list[RecordMatch]:
        matches, _ = self.search_page(request, limit=k, offset=0)
        return matches

    def search_page(
        self,
        request: SimilaritySearchRequest,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[RecordMatch], int]:
        tsquery = func.websearch_to_tsquery("english", request.query_text.strip())
        rank = func.ts_rank_cd(
            ParliamentaryRecord.search_vector,
            tsquery,
        ).label("lexical_score")
        match_condition = ParliamentaryRecord.search_vector.op("@@")(tsquery)

        query = select(ParliamentaryRecord, rank).where(match_condition)
        query = self._apply_filters(query, request)
        rows = self._db.execute(
            query.order_by(
                rank.desc(),
                ParliamentaryRecord.created_at.desc(),
                ParliamentaryRecord.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()

        count_query = select(func.count(ParliamentaryRecord.id)).where(
            match_condition
        )
        count_query = self._apply_filters(count_query, request)
        total = self._db.scalar(count_query) or 0
        matched_terms = sorted(
            {
                term
                for term in TERM_PATTERN.findall(request.query_text.casefold())
                if len(term) > 2
            }
        )
        matches = [
            RecordMatch(
                record_id=UUID(str(row.ParliamentaryRecord.id)),
                score=round(max(0.0, min(1.0, float(row.lexical_score))), 6),
                lexical_rank=offset + index,
                metadata={
                    "subject": row.ParliamentaryRecord.subject,
                    "member": row.ParliamentaryRecord.member,
                    "ministry": row.ParliamentaryRecord.ministry,
                    "matched_terms": matched_terms,
                    "lexical_score": float(row.lexical_score),
                },
            )
            for index, row in enumerate(rows, start=1)
        ]
        return matches, int(total)

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
            query = query.where(func.date(ParliamentaryRecord.created_at) == request.date)
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


# Transitional import alias for callers that used the prototype name.
BM25LexicalRetriever = PostgresLexicalRetriever
