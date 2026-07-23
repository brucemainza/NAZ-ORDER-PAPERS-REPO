from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip, require_permission
from app.models import ParliamentaryRecord, ParliamentarySession, User
from app.schemas.search import SearchResultOut
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionRecordOut,
    SubmissionResponse,
)
from app.services.similarity import find_previously_addressed_candidates

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("/review-queue", response_model=list[SubmissionRecordOut])
def review_queue(
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_permission("review_submission")),
) -> list[ParliamentaryRecord]:
    return list(
        db.scalars(
            select(ParliamentaryRecord)
            .where(
                ParliamentaryRecord.status.in_(
                    ("Under Review", "Pending Review")
                )
            )
            .order_by(ParliamentaryRecord.created_at.asc())
        ).all()
    )


@router.post("", response_model=SubmissionResponse, status_code=201)
def create_submission(
    submission: SubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionResponse:
    if submission.item_type == "Question" and not user.has_permission("submit_question"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if submission.item_type == "Motion" and not user.has_permission("submit_motion"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    session = db.execute(
        select(ParliamentarySession).where(ParliamentarySession.id == submission.session_id)
    ).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Parliamentary session not found")
    if session.status not in {"Active", "Upcoming"}:
        raise HTTPException(status_code=400, detail="Submissions can only be added to active or upcoming sessions")

    record = ParliamentaryRecord(
        item_type=submission.item_type,
        session_id=submission.session_id,
        member=submission.member.strip(),
        ministry=submission.ministry.strip() if submission.ministry else None,
        answer_type=submission.answer_type,
        subject=submission.subject.strip(),
        full_text=submission.full_text.strip(),
        status="Under Review",
    )
    db.add(record)
    db.flush()
    add_audit_log(
        db,
        user_id=user.id,
        action="record_submission",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=f"{record.item_type}: {record.subject}",
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(record)

    candidates = find_previously_addressed_candidates(db, record=record, limit=5)
    return SubmissionResponse(
        record=record,
        candidates=[
            SearchResultOut(
                rank=index + 1,
                score=match.score,
                matched_terms=match.matched_terms,
                record=match.record,
            )
            for index, match in enumerate(candidates)
        ],
    )
