from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord, QuestionResponse


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

    def __init__(self, db: Session) -> None:
        self._db = db

    def record_response(
        self,
        *,
        record_id: UUID,
        response_text: str,
        response_date: date,
        recorded_by: UUID,
    ) -> QuestionResponse:
        record = self._db.get(ParliamentaryRecord, record_id)
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
        self._db.flush()
        return response
