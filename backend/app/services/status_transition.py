from abc import ABC, abstractmethod

from app.models import ParliamentaryRecord
from app.services.submission_status import SubmissionStatus, transition_submission


class StatusTransitioner(ABC):
    @abstractmethod
    def transition(
        self,
        record: ParliamentaryRecord,
        target_status: SubmissionStatus,
    ) -> None:
        """Apply lifecycle policy without owning persistence."""


class SubmissionStatusTransitioner(StatusTransitioner):
    def transition(
        self,
        record: ParliamentaryRecord,
        target_status: SubmissionStatus,
    ) -> None:
        transition_submission(record, target_status)


def get_status_transitioner() -> StatusTransitioner:
    return SubmissionStatusTransitioner()
