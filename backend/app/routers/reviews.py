from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import ParliamentaryRecord, ReviewDecision, User
from app.schemas.review import ReviewDecisionCreate, ReviewDecisionOut
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

router = APIRouter(prefix="/records/{record_id}/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewDecisionOut])
def list_review_decisions(
    record_id: UUID,
    cursor: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> list[ReviewDecisionOut]:
    query = (
        select(ReviewDecision, User.name)
        .outerjoin(User, ReviewDecision.reviewer_id == User.id)
        .where(ReviewDecision.record_id == record_id)
        .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
        .limit(limit)
    )
    if cursor is not None:
        cursor_row = db.scalar(
            select(ReviewDecision).where(
                ReviewDecision.id == cursor,
                ReviewDecision.record_id == record_id,
            )
        )
        if cursor_row is None:
            raise HTTPException(status_code=404, detail="Review cursor not found")
        query = query.where(
            or_(
                ReviewDecision.created_at < cursor_row.created_at,
                and_(
                    ReviewDecision.created_at == cursor_row.created_at,
                    ReviewDecision.id < cursor_row.id,
                ),
            )
        )
    rows = db.execute(query).all()
    return [
        ReviewDecisionOut(
            id=decision.id,
            record_id=decision.record_id,
            similar_record_id=decision.similar_record_id,
            decision=decision.decision,
            is_duplicate=decision.is_duplicate,
            reviewer_id=decision.reviewer_id,
            reviewer_name=reviewer_name,
            notes=decision.notes,
            created_at=decision.created_at,
        )
        for decision, reviewer_name in rows
    ]


@router.post("", response_model=ReviewDecisionOut, status_code=201)
def record_review_decision(
    record_id: UUID,
    decision_in: ReviewDecisionCreate,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> ReviewDecisionOut:
    payload = {
        "record_id": str(record_id),
        **decision_in.model_dump(mode="json"),
    }
    try:
        idempotency = claim_idempotency_key(
            db,
            scope=f"review:create:{user.id}",
            key=idempotency_key,
            payload=payload,
            user_id=user.id,
        )
    except (IdempotencyConflict, IdempotencyInProgress) as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    cached_response = cached_idempotency_response(idempotency)
    if cached_response is not None:
        return ReviewDecisionOut.model_validate(cached_response)

    record = db.scalar(
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.id == record_id)
        .with_for_update()
    )
    if not record:
        db.rollback()
        raise HTTPException(status_code=404, detail="Record not found")
    if decision_in.similar_record_id == record_id:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="A record cannot be marked similar to itself",
        )
    if decision_in.similar_record_id:
        similar = db.execute(
            select(ParliamentaryRecord).where(ParliamentaryRecord.id == decision_in.similar_record_id)
        ).scalars().first()
        if not similar:
            db.rollback()
            raise HTTPException(status_code=404, detail="Similar record not found")

    is_duplicate = decision_in.decision in {"Duplicate", "Substantially Similar"}
    decision = ReviewDecision(
        record_id=record.id,
        similar_record_id=decision_in.similar_record_id,
        decision=decision_in.decision,
        is_duplicate=is_duplicate,
        reviewer_id=user.id,
        notes=decision_in.notes,
    )
    db.add(decision)
    try:
        flush_transaction(
            db,
            conflict_message="The review conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    add_audit_log(
        db,
        user_id=user.id,
        action="duplicate_review",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=decision_in.decision,
        ip_address=request_ip(request),
    )
    response = ReviewDecisionOut(
        id=decision.id,
        record_id=decision.record_id,
        similar_record_id=decision.similar_record_id,
        decision=decision.decision,
        is_duplicate=decision.is_duplicate,
        reviewer_id=decision.reviewer_id,
        reviewer_name=user.name,
        notes=decision.notes,
        created_at=decision.created_at,
    )
    complete_idempotency_key(
        idempotency,
        response_status=201,
        response_body=response.model_dump(mode="json"),
        resource_type="review_decision",
        resource_id=str(decision.id),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The review conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response
