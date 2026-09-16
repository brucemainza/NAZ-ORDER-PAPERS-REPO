from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_ai_service, get_ai_settings, get_embedding_provider
from app.ai.indexing.chunks import chunk_index_coverage, enqueue_chunk_backfill
from app.ai.schemas import (
    AIHealthResponse,
    AIReviewSubmission,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from app.ai.service import AISimilarityService
from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip, require_permission
from app.models import ParliamentaryRecord, ReviewDecision, User
from app.jobs.queue import enqueue_outbox_job
from app.services.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    cached_idempotency_response,
    claim_idempotency_key,
    complete_idempotency_key,
)
from app.services.transactions import (
    DatabaseConflict,
    commit_transaction,
    flush_transaction,
)

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


@router.get("/index/coverage")
def index_coverage(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
    embedding_provider=Depends(get_embedding_provider),
    settings=Depends(get_ai_settings),
) -> dict:
    coverage = chunk_index_coverage(
        db,
        model=embedding_provider.model_name,
        model_digest=embedding_provider.model_digest,
        dimension=embedding_provider.dimension,
        preprocessing_version=settings.ai_preprocessing_version,
    )
    return {
        "eligible_records": coverage.eligible_records,
        "indexed_records": coverage.indexed_records,
        "coverage_percent": coverage.coverage_percent,
        "model": embedding_provider.model_name,
        "model_digest": embedding_provider.model_digest,
        "preprocessing_version": settings.ai_preprocessing_version,
    }


@router.post("/index/{record_id}", status_code=202)
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
    content_hash = sha256(text.encode("utf-8")).hexdigest()
    job = enqueue_outbox_job(
        db,
        job_type="embed_record",
        payload={
            "record_id": str(record.id),
            "record_version": record.version,
            "content_hash": content_hash,
            "model": embedding_provider.model_name,
            "model_digest": embedding_provider.model_digest,
        },
        deduplication_key=(
            f"embed_record:{record.id}:{record.version}:{content_hash}:"
            f"{embedding_provider.model_digest}"
        ),
        aggregate_type="parliamentary_record",
        aggregate_id=str(record.id),
        event_type="record.indexing_requested",
    )
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
    return {
        "record_id": record_id,
        "job_id": job.id,
        "indexed": False,
        "queued": True,
        "model": embedding_provider.model_name,
        "model_digest": embedding_provider.model_digest,
    }


@router.post("/reindex")
def reindex_all(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
    after_id: UUID | None = None,
    limit: int = 100,
    embedding_provider=Depends(get_embedding_provider),
    settings=Depends(get_ai_settings),
) -> dict:
    limit = max(1, min(limit, 500))
    result = enqueue_chunk_backfill(
        db,
        model=embedding_provider.model_name,
        model_digest=embedding_provider.model_digest,
        preprocessing_version=settings.ai_preprocessing_version,
        after_id=after_id,
        limit=limit,
    )
    add_audit_log(
        db,
        user_id=user.id,
        action="ai_reindex",
        entity_type="ai_index",
        entity_id=str(result.next_cursor) if result.next_cursor else None,
        details=f"queued={result.queued};complete={result.complete}",
        ip_address=request_ip(request),
    )
    db.commit()
    return {
        "queued": result.queued,
        "next_cursor": result.next_cursor,
        "complete": result.complete,
        "model": embedding_provider.model_name,
        "model_digest": embedding_provider.model_digest,
        "preprocessing_version": settings.ai_preprocessing_version,
    }


@router.post("/review")
def submit_ai_review(
    review: AIReviewSubmission,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> dict:
    try:
        idempotency = claim_idempotency_key(
            db,
            scope=f"ai-review:create:{user.id}",
            key=idempotency_key,
            payload=review.model_dump(mode="json"),
            user_id=user.id,
        )
    except (IdempotencyConflict, IdempotencyInProgress) as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    cached_response = cached_idempotency_response(idempotency)
    if cached_response is not None:
        return cached_response

    record = db.scalar(
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.id == review.record_id)
        .with_for_update()
    )
    if record is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Record not found")
    if review.similar_record_id is not None:
        similar = db.get(ParliamentaryRecord, review.similar_record_id)
        if similar is None:
            db.rollback()
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
    try:
        flush_transaction(
            db,
            conflict_message="The AI review conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    add_audit_log(
        db,
        user_id=user.id,
        action="ai_review",
        entity_type="parliamentary_record",
        entity_id=str(review.record_id),
        details=review.decision,
        ip_address=request_ip(request),
    )
    response_body = {"review_id": str(decision.id)}
    complete_idempotency_key(
        idempotency,
        response_status=200,
        response_body=response_body,
        resource_type="review_decision",
        resource_id=str(decision.id),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The AI review conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response_body
