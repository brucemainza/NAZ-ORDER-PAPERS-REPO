from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import ParliamentaryRecord, ReviewDecision, User
from app.schemas.review import ReviewDecisionCreate, ReviewDecisionOut

router = APIRouter(prefix="/records/{record_id}/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewDecisionOut])
def list_review_decisions(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> list[ReviewDecisionOut]:
    rows = db.execute(
        select(ReviewDecision, User.name)
        .outerjoin(User, ReviewDecision.reviewer_id == User.id)
        .where(ReviewDecision.record_id == record_id)
        .order_by(ReviewDecision.created_at.desc())
    ).all()
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
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("review_submission")),
) -> ReviewDecisionOut:
    record = db.execute(select(ParliamentaryRecord).where(ParliamentaryRecord.id == record_id)).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if decision_in.similar_record_id:
        similar = db.execute(
            select(ParliamentaryRecord).where(ParliamentaryRecord.id == decision_in.similar_record_id)
        ).scalars().first()
        if not similar:
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
    db.flush()
    add_audit_log(
        db,
        user_id=user.id,
        action="duplicate_review",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=decision_in.decision,
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(decision)

    return ReviewDecisionOut(
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
