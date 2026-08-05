from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_ai_service
from app.ai.retrieval.lexical import PostgresLexicalRetriever
from app.ai.schemas import SimilaritySearchRequest
from app.ai.service import AISimilarityService
from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip
from app.models import ParliamentaryRecord, SearchLog, User
from app.schemas.search import SearchRequest, SearchResponse, SearchResultOut

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_records(
    search: SearchRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    ai_service: AISimilarityService = Depends(get_ai_service),
) -> SearchResponse:
    if search.mode == "hybrid":
        return _hybrid_search(search, request, db, user, ai_service)
    return _keyword_search(search, request, db, user)


def _keyword_search(
    search: SearchRequest,
    request: Request,
    db: Session,
    user: User,
) -> SearchResponse:
    ai_request = SimilaritySearchRequest(
        query_text=search.query_text,
        session_id=search.session_id,
        item_type=search.item_type,
        status=search.status,
        date=search.date,
        member=search.member,
        ministry=search.ministry,
    )
    ranked_matches, total_results = PostgresLexicalRetriever(
        db, user
    ).search_page(
        ai_request,
        limit=search.limit,
        offset=search.offset,
    )
    result_ids = [match.record_id for match in ranked_matches]
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

    records = {
        record.id: record
        for record in db.scalars(
            select(ParliamentaryRecord).where(ParliamentaryRecord.id.in_(result_ids))
        ).all()
    }
    results = [
        SearchResultOut(
            rank=search.offset + index + 1,
            score=round(match.score * 100, 2),
            matched_terms=match.metadata.get("matched_terms", []),
            record=records[match.record_id],
        )
        for index, match in enumerate(ranked_matches)
        if match.record_id in records
    ]

    return SearchResponse(
        query_text=search.query_text,
        total_candidates=total_results,
        total_results=total_results,
        results=results,
    )


def _hybrid_search(
    search: SearchRequest,
    request: Request,
    db: Session,
    user: User,
    ai_service: AISimilarityService,
) -> SearchResponse:
    ai_request = SimilaritySearchRequest(
        query_text=search.query_text,
        session_id=search.session_id,
        item_type=search.item_type,
        status=search.status,
        date=search.date,
        member=search.member,
        ministry=search.ministry,
        limit=search.limit,
        offset=search.offset,
    )
    response = ai_service.search(ai_request)

    result_ids = [match.record_id for match in response.results]
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
        action="hybrid_search",
        entity_type="search_log",
        details=search.query_text,
        ip_address=request_ip(request),
    )
    db.commit()

    records = {
        item.id: item
        for item in db.execute(
            select(ParliamentaryRecord).where(ParliamentaryRecord.id.in_(result_ids))
        ).scalars().all()
    }

    results = [
        SearchResultOut(
            rank=search.offset + index + 1,
            score=round(match.score * 100, 2),
            matched_terms=match.metadata.get("matched_terms", ["semantic"]),
            record=records[match.record_id],
        )
        for index, match in enumerate(response.results)
        if match.record_id in records
    ]

    return SearchResponse(
        query_text=search.query_text,
        total_candidates=response.total_lexical + response.total_semantic,
        total_results=len(response.results),
        results=results,
    )
