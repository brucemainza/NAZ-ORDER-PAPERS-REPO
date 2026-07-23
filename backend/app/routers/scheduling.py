from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import ParliamentaryRecord, User
from app.schemas.submission import SubmissionRecordOut, SubmissionSchedule
from app.services.submission_status import (
    InvalidStatusTransition,
    SubmissionStatus,
    transition_submission,
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
    db: Session = Depends(get_db),
    scheduler: User = Depends(require_permission("schedule_item")),
) -> ParliamentaryRecord:
    record = db.get(ParliamentaryRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    try:
        transition_submission(record, SubmissionStatus.SCHEDULED)
    except InvalidStatusTransition as error:
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
    db.commit()
    db.refresh(record)
    return record
