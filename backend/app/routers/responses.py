from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
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
from app.services.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    cached_idempotency_response,
    claim_idempotency_key,
    complete_idempotency_key,
)
from app.services.transactions import DatabaseConflict, commit_transaction

router = APIRouter(
    prefix="/records/{record_id}/response",
    tags=["responses"],
)


@router.post("", response_model=QuestionResponseOut, status_code=201)
def record_question_response(
    record_id: UUID,
    response_in: QuestionResponseCreate,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
    db: Session = Depends(get_db),
    clerk: User = Depends(require_permission("record_response")),
    recorder: ResponseRecorder = Depends(get_response_recorder),
) -> QuestionResponseOut:
    try:
        idempotency = claim_idempotency_key(
            db,
            scope=f"question-response:create:{clerk.id}",
            key=idempotency_key,
            payload={
                "record_id": str(record_id),
                **response_in.model_dump(mode="json"),
            },
            user_id=clerk.id,
        )
    except (IdempotencyConflict, IdempotencyInProgress) as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    cached_response = cached_idempotency_response(idempotency)
    if cached_response is not None:
        return QuestionResponseOut.model_validate(cached_response)

    try:
        response = recorder.record_response(
            record_id=record_id,
            response_text=response_in.response_text,
            response_date=response_in.response_date,
            recorded_by=clerk.id,
        )
    except ResponseRecordNotFound as error:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ResponseRecordingConflict as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A response has already been recorded for this question",
        ) from error

    add_audit_log(
        db,
        user_id=clerk.id,
        action="question_response_recording",
        entity_type="parliamentary_record",
        entity_id=str(record_id),
        details=response.response_date.isoformat(),
        ip_address=request_ip(request),
    )
    response_out = QuestionResponseOut(
        id=response.id,
        record_id=response.record_id,
        response_text=response.response_text,
        response_date=response.response_date,
        recorded_by=response.recorded_by,
        status=response.record.status,
        created_at=response.created_at,
    )
    complete_idempotency_key(
        idempotency,
        response_status=201,
        response_body=response_out.model_dump(mode="json"),
        resource_type="question_response",
        resource_id=str(response.id),
    )
    try:
        commit_transaction(
            db,
            conflict_message="A response has already been recorded for this question",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response_out
