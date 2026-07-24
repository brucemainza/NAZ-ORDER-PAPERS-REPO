from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import User
from app.responses.dependencies import get_response_recorder
from app.responses.service import (
    ResponseRecorder,
    ResponseRecordingConflict,
    ResponseRecordNotFound,
)
from app.schemas.response import QuestionResponseCreate, QuestionResponseOut

router = APIRouter(
    prefix="/records/{record_id}/response",
    tags=["responses"],
)


@router.post("", response_model=QuestionResponseOut, status_code=201)
def record_question_response(
    record_id: UUID,
    response_in: QuestionResponseCreate,
    request: Request,
    db: Session = Depends(get_db),
    clerk: User = Depends(require_permission("record_response")),
    recorder: ResponseRecorder = Depends(get_response_recorder),
) -> QuestionResponseOut:
    try:
        response = recorder.record_response(
            record_id=record_id,
            response_text=response_in.response_text,
            response_date=response_in.response_date,
            recorded_by=clerk.id,
        )
    except ResponseRecordNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ResponseRecordingConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    add_audit_log(
        db,
        user_id=clerk.id,
        action="question_response_recording",
        entity_type="parliamentary_record",
        entity_id=str(record_id),
        details=response.response_date.isoformat(),
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(response)
    return QuestionResponseOut(
        id=response.id,
        record_id=response.record_id,
        response_text=response.response_text,
        response_date=response.response_date,
        recorded_by=response.recorded_by,
        status=response.record.status,
        created_at=response.created_at,
    )
