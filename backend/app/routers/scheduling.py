from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import ParliamentaryRecord, User
from app.notifications.dependencies import get_status_change_notifier
from app.notifications.service import StatusChangeNotifier
from app.notifications.tasks import enqueue_status_change_notification
from app.schemas.submission import SubmissionRecordOut, SubmissionSchedule
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
    prefix="/submissions/{record_id}/schedule",
    tags=["scheduling"],
)


@router.post("", response_model=SubmissionRecordOut)
def schedule_submission(
    record_id: UUID,
    schedule: SubmissionSchedule,
    request: Request,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
    db: Session = Depends(get_db),
    scheduler: User = Depends(require_permission("schedule_item")),
    notifier: StatusChangeNotifier = Depends(get_status_change_notifier),
) -> SubmissionRecordOut:
    try:
        idempotency = claim_idempotency_key(
            db,
            scope=f"submission:schedule:{scheduler.id}",
            key=idempotency_key,
            payload={
                "record_id": str(record_id),
                **schedule.model_dump(mode="json"),
            },
            user_id=scheduler.id,
        )
    except (IdempotencyConflict, IdempotencyInProgress) as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    cached_response = cached_idempotency_response(idempotency)
    if cached_response is not None:
        return SubmissionRecordOut.model_validate(cached_response)

    record = db.scalar(
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.id == record_id)
        .with_for_update()
    )
    if not record:
        db.rollback()
        raise HTTPException(status_code=404, detail="Record not found")
    if not (
        record.session.start_date
        <= schedule.sitting_date
        <= record.session.end_date
    ):
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="Sitting date must fall within the parliamentary session",
        )

    old_status = record.status
    try:
        transition_submission(record, SubmissionStatus.SCHEDULED)
    except InvalidStatusTransition as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error

    record.sitting_date = schedule.sitting_date
    add_audit_log(
        db,
        user_id=scheduler.id,
        action="submission_scheduling",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=schedule.sitting_date.isoformat(),
        ip_address=request_ip(request),
    )
    try:
        flush_transaction(
            db,
            conflict_message="The record was scheduled by another operation",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    response = SubmissionRecordOut.model_validate(record)
    complete_idempotency_key(
        idempotency,
        response_status=200,
        response_body=response.model_dump(mode="json"),
        resource_type="parliamentary_record",
        resource_id=str(record.id),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The record was scheduled by another operation",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
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
    return response
