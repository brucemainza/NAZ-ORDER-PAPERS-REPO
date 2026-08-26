from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord, QuestionResponse
from app.services.status_transition import StatusTransitioner
from app.services.submission_status import SubmissionStatus


class ResponseRecordNotFound(LookupError):
    pass


class ResponseRecordingConflict(ValueError):
    pass


class ResponseRecorder(ABC):
    @abstractmethod
    def record_response(
        self,
        *,
        record_id: UUID,
        response_text: str,
        response_date: date,
        recorded_by: UUID,
    ) -> QuestionResponse:
        """Record one response for an eligible scheduled question."""


class ResponseRecordingService(ResponseRecorder):
    """Validates and persists response content without owning status policy."""

    def __init__(
        self,
        db: Session,
        *,
        status_transitioner: StatusTransitioner,
    ) -> None:
        self._db = db
        self._status_transitioner = status_transitioner

    def record_response(
        self,
        *,
        record_id: UUID,
        response_text: str,
        response_date: date,
        recorded_by: UUID,
    ) -> QuestionResponse:
        record = self._db.scalar(
            select(ParliamentaryRecord)
            .where(ParliamentaryRecord.id == record_id)
            .with_for_update()
        )
        if record is None:
            raise ResponseRecordNotFound("Question not found")
        if record.item_type != "Question":
            raise ResponseRecordingConflict(
                "Responses can only be recorded for questions"
            )
        if record.status != "Scheduled":
            raise ResponseRecordingConflict(
                "A response can only be recorded for a Scheduled question"
            )
        existing_response = self._db.scalar(
            select(QuestionResponse).where(
                QuestionResponse.record_id == record.id
            )
        )
        if existing_response is not None:
            raise ResponseRecordingConflict(
                "A response has already been recorded for this question"
            )

        response = QuestionResponse(
            record_id=record.id,
            response_text=response_text.strip(),
            response_date=response_date,
            recorded_by=recorded_by,
        )
        self._db.add(response)
        try:
            self._status_transitioner.transition(
                record,
                SubmissionStatus.ANSWERED,
            )
            self._db.flush()
        except Exception:
            self._db.rollback()
            raise

        return response
