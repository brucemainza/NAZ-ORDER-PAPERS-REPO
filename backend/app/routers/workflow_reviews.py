from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip
from app.models import ParliamentaryRecord, User, WorkflowDecision
from app.notifications.tasks import enqueue_status_change_notification
from app.schemas.review import WorkflowReviewCreate, WorkflowReviewOut
from app.services.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    cached_idempotency_response,
    claim_idempotency_key,
    complete_idempotency_key,
)
from app.services.submission_status import (
    InvalidStatusTransition,
    SubmissionStatus,
    transition_submission,
)
from app.services.transactions import (
    DatabaseConflict,
    commit_transaction,
    flush_transaction,
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
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
    db: Session = Depends(get_db),
    reviewer: User = Depends(get_current_user),
) -> WorkflowReviewOut:
    permission, next_status = ACTION_RULES[review.action]
    if not reviewer.has_permission(permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        idempotency = claim_idempotency_key(
            db,
            scope=f"submission:workflow-review:{reviewer.id}",
            key=idempotency_key,
            payload={
                "record_id": str(record_id),
                **review.model_dump(mode="json"),
            },
            user_id=reviewer.id,
        )
    except (IdempotencyConflict, IdempotencyInProgress) as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    cached_response = cached_idempotency_response(idempotency)
    if cached_response is not None:
        return WorkflowReviewOut.model_validate(cached_response)

    record = db.scalar(
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.id == record_id)
        .with_for_update()
    )
    if not record:
        db.rollback()
        raise HTTPException(status_code=404, detail="Record not found")
    old_status = record.status
    try:
        transition_submission(record, next_status)
    except InvalidStatusTransition as error:
        db.rollback()
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
    try:
        flush_transaction(
            db,
            conflict_message="The workflow state changed in another operation",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    add_audit_log(
        db,
        user_id=reviewer.id,
        action="workflow_review",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=f"{review.action}: {next_status.value}",
        ip_address=request_ip(request),
    )
    response = WorkflowReviewOut(
        id=decision.id,
        record_id=decision.record_id,
        action=decision.action,
        status=next_status.value,
        reviewer_id=decision.reviewer_id,
        reviewer_name=reviewer.name,
        notes=decision.notes,
        created_at=decision.created_at,
    )
    enqueue_status_change_notification(
        db,
        event_key=f"workflow-decision:{decision.id}",
        recipient=record.submitter.email if record.submitter else None,
        record_id=record.id,
        item_type=record.item_type,
        subject=record.subject,
        old_status=old_status,
        new_status=record.status,
    )
    complete_idempotency_key(
        idempotency,
        response_status=201,
        response_body=response.model_dump(mode="json"),
        resource_type="workflow_decision",
        resource_id=str(decision.id),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The workflow state changed in another operation",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response
