from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.dependencies import get_ai_service, get_embedding_provider
from app.ai.schemas import (
    AIExplainRequest,
    AIExplanation,
    AIHealthResponse,
    AIReviewSubmission,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from app.ai.service import AISimilarityService
from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip, require_permission
from app.models import ParliamentaryRecord, ReviewDecision, User
from app.services.record_visibility import can_view_record

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health", response_model=AIHealthResponse)
def ai_health(
    service: AISimilarityService = Depends(get_ai_service),
) -> AIHealthResponse:
    return service.health()


@router.post("/search", response_model=SimilaritySearchResponse)
def ai_search(
    search_request: SimilaritySearchRequest,
    request: Request,
    service: AISimilarityService = Depends(get_ai_service),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SimilaritySearchResponse:
    response = service.search(search_request)
    add_audit_log(
        db,
        user_id=user.id,
        action="ai_search",
        entity_type="ai",
        details=f"results={len(response.results)}",
        ip_address=request_ip(request),
    )
    db.commit()
    return response


@router.post("/explain", response_model=AIExplanation)
def ai_explain(
    explain_request: AIExplainRequest,
    request: Request,
    service: AISimilarityService = Depends(get_ai_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> AIExplanation:
    records = list(
        db.query(ParliamentaryRecord)
        .filter(ParliamentaryRecord.id.in_(explain_request.record_ids))
        .all()
    )
    records_by_id = {record.id: record for record in records}
    if len(records_by_id) != len(set(explain_request.record_ids)):
        raise HTTPException(status_code=404, detail="One or more evidence records not found")

    ordered_records = []
    for record_id in explain_request.record_ids:
        record = records_by_id.get(record_id)
        if record is None or not can_view_record(record, user):
            # Do not disclose whether a restricted record exists.
            raise HTTPException(
                status_code=404,
                detail="One or more evidence records not found",
            )
        ordered_records.append(record)

    evidence = [
        {
            "record_id": record.id,
            "subject": record.subject,
            "full_text": record.full_text,
            "member": record.member,
            "ministry": record.ministry,
            "session": record.session.name if record.session else None,
            "sitting_date": record.sitting_date.isoformat() if record.sitting_date else None,
            "status": record.status,
        }
        for record in ordered_records
    ]
    explanation = service.explain(explain_request.query_text, evidence)
    allowed_ids = set(explain_request.record_ids)
    explanation = explanation.model_copy(
        update={
            "supporting_record_ids": [
                record_id
                for record_id in explanation.supporting_record_ids
                if record_id in allowed_ids
            ],
            "human_review_required": True,
        }
    )
    add_audit_log(
        db,
        user_id=user.id,
        action="ai_explanation",
        entity_type="parliamentary_record",
        entity_id=",".join(str(record_id) for record_id in explain_request.record_ids),
        details=f"classification={explanation.classification};model={explanation.model}",
        ip_address=request_ip(request),
    )
    db.commit()
    return explanation


@router.post("/index/{record_id}")
def index_record(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
    embedding_provider=Depends(get_embedding_provider),
) -> dict:
    record = db.get(ParliamentaryRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    from app.similarity.duplicate_detection import build_similarity_text

    text = build_similarity_text(record.subject, record.full_text)
    record.embedding = embedding_provider.embed_query(text)
    record.embedding_model = embedding_provider.model_name
    add_audit_log(
        db,
        user_id=user.id,
        action="ai_index",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=f"model={embedding_provider.model_name}",
        ip_address=request_ip(request),
    )
    db.commit()
    return {"record_id": record_id, "indexed": True, "model": embedding_provider.model_name}


@router.post("/reindex")
def reindex_all(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> dict:
    # Full batch re-indexing is delegated to scripts/reindex_records.py for
    # memory and latency control. This endpoint just validates permission.
    raise HTTPException(
        status_code=501,
        detail="Use scripts/reindex_records.py for batch re-indexing",
    )


@router.post("/review")
def submit_ai_review(
    review: AIReviewSubmission,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> dict:
    record = db.get(ParliamentaryRecord, review.record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    if review.similar_record_id is not None:
        similar = db.get(ParliamentaryRecord, review.similar_record_id)
        if similar is None:
            raise HTTPException(status_code=404, detail="Similar record not found")

    decision = ReviewDecision(
        record_id=review.record_id,
        similar_record_id=review.similar_record_id,
        decision=review.decision,
        notes=review.notes,
        reviewer_id=user.id,
        is_duplicate=review.decision in {"Duplicate", "Substantially Similar"},
    )
    db.add(decision)
    db.flush()
    add_audit_log(
        db,
        user_id=user.id,
        action="ai_review",
        entity_type="parliamentary_record",
        entity_id=str(review.record_id),
        details=review.decision,
        ip_address=request_ip(request),
    )
    db.commit()
    return {"review_id": decision.id}
