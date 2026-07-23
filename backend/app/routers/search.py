from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip
from app.models import ParliamentaryRecord, SearchLog, User
from app.retrieval.bm25 import rank_records
from app.schemas.search import SearchRequest, SearchResponse, SearchResultOut
from app.services.record_visibility import (
    restrict_archive_visibility,
    restrict_draft_visibility,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_records(
    search: SearchRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SearchResponse:
    query = select(ParliamentaryRecord)
    query = restrict_draft_visibility(query, user)
    query = restrict_archive_visibility(query, user, "search_archive")

    if search.session_id:
        query = query.where(ParliamentaryRecord.session_id == search.session_id)

    if search.item_type:
        query = query.where(
            func.lower(ParliamentaryRecord.item_type)
            == search.item_type.strip().lower()
        )

    if search.status:
        query = query.where(
            func.lower(ParliamentaryRecord.status)
            == search.status.strip().lower()
        )

    if search.date:
        query = query.where(
            func.date(ParliamentaryRecord.created_at) == search.date
        )

    if search.member:
        query = query.where(
            ParliamentaryRecord.member.ilike(f"%{search.member.strip()}%")
        )

    if search.ministry:
        query = query.where(
            ParliamentaryRecord.ministry.ilike(f"%{search.ministry.strip()}%")
        )

    query = query.order_by(
        ParliamentaryRecord.created_at.desc(),
        ParliamentaryRecord.id.asc(),
    )
    records = list(db.execute(query).scalars().all())
    all_ranked_matches = rank_records(
        search.query_text,
        records,
        len(records),
    )
    ranked_matches = all_ranked_matches[
        search.offset : search.offset + search.limit
    ]

    result_ids = [match.record.id for match in ranked_matches]
    db.add(
        SearchLog(
            user_id=user.id,
            query_text=search.query_text,
            session_id=search.session_id,
            top_result_ids=result_ids,
        )
    )
    add_audit_log(
        db,
        user_id=user.id,
        action="search",
        entity_type="search_log",
        details=search.query_text,
        ip_address=request_ip(request),
    )
    db.commit()

    results = [
        SearchResultOut(
            rank=search.offset + index + 1,
            score=match.score,
            matched_terms=match.matched_terms,
            record=match.record,
        )
        for index, match in enumerate(ranked_matches)
    ]

    return SearchResponse(
        query_text=search.query_text,
        total_candidates=len(records),
        total_results=len(all_ranked_matches),
        results=results,
    )
