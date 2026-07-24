from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip
from app.models import ParliamentaryRecord, User, WorkflowDecision
from app.notifications.dependencies import get_status_change_notifier
from app.notifications.service import StatusChangeNotifier
from app.notifications.tasks import enqueue_status_change_notification
from app.schemas.review import WorkflowReviewCreate, WorkflowReviewOut
from app.services.submission_status import (
    InvalidStatusTransition,
    SubmissionStatus,
    transition_submission,
)

router = APIRouter(
    prefix="/submissions/{record_id}/workflow-review",
    tags=["workflow reviews"],
)

ACTION_RULES = {
    "Approve": ("approve_motion", SubmissionStatus.APPROVED),
    "Reject": ("reject_submission", SubmissionStatus.REJECTED),
    "Request Changes": ("request_changes", SubmissionStatus.DRAFT),
}


@router.post("", response_model=WorkflowReviewOut, status_code=201)
def review_submission(
    record_id: UUID,
    review: WorkflowReviewCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    reviewer: User = Depends(get_current_user),
    notifier: StatusChangeNotifier = Depends(get_status_change_notifier),
) -> WorkflowReviewOut:
    permission, next_status = ACTION_RULES[review.action]
    if not reviewer.has_permission(permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    record = db.get(ParliamentaryRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    old_status = record.status
    try:
        transition_submission(record, next_status)
    except InvalidStatusTransition as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    decision = WorkflowDecision(
        record_id=record.id,
        action=review.action,
        notes=review.notes,
        reviewer_id=reviewer.id,
    )
    db.add(decision)
    db.flush()
    add_audit_log(
        db,
        user_id=reviewer.id,
        action="workflow_review",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=f"{review.action}: {next_status.value}",
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(decision)
    enqueue_status_change_notification(
        background_tasks,
        notifier,
        recipient=record.submitter.email if record.submitter else None,
        record_id=record.id,
        item_type=record.item_type,
        subject=record.subject,
        old_status=old_status,
        new_status=record.status,
    )

    return WorkflowReviewOut(
        id=decision.id,
        record_id=decision.record_id,
        action=decision.action,
        status=next_status.value,
        reviewer_id=decision.reviewer_id,
        reviewer_name=reviewer.name,
        notes=decision.notes,
        created_at=decision.created_at,
    )
