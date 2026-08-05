from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from app.deps import get_current_user, require_permission
from app.models import ParliamentaryRecord, User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health", response_model=AIHealthResponse)
def ai_health(
    service: AISimilarityService = Depends(get_ai_service),
) -> AIHealthResponse:
    return service.health()


@router.post("/search", response_model=SimilaritySearchResponse)
def ai_search(
    request: SimilaritySearchRequest,
    service: AISimilarityService = Depends(get_ai_service),
) -> SimilaritySearchResponse:
    return service.search(request)


@router.post("/explain", response_model=AIExplanation)
def ai_explain(
    request: AIExplainRequest,
    service: AISimilarityService = Depends(get_ai_service),
    db: Session = Depends(get_db),
) -> AIExplanation:
    records = list(
        db.query(ParliamentaryRecord)
        .filter(ParliamentaryRecord.id.in_(request.record_ids))
        .all()
    )
    if len(records) != len(request.record_ids):
        raise HTTPException(status_code=404, detail="One or more evidence records not found")

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
        for record in records
    ]
    return service.explain(request.query_text, evidence)


@router.post("/index/{record_id}")
def index_record(
    record_id: UUID,
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
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> dict:
    from app.models import ReviewDecision

    decision = ReviewDecision(
        record_id=review.record_id,
        similar_record_id=review.similar_record_id,
        decision=review.decision,
        notes=review.notes,
        reviewer_id=user.id,
        is_duplicate=review.decision in {"duplicate", "similar"},
    )
    db.add(decision)
    db.commit()
    return {"review_id": decision.id}
