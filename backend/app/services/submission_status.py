from enum import StrEnum


class SubmissionStatus(StrEnum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    SCHEDULED = "Scheduled"
    ARCHIVED = "Archived"


ALLOWED_TRANSITIONS = {
    SubmissionStatus.DRAFT: {
        SubmissionStatus.SUBMITTED,
        SubmissionStatus.ARCHIVED,
    },
    SubmissionStatus.SUBMITTED: {
        SubmissionStatus.UNDER_REVIEW,
        SubmissionStatus.ARCHIVED,
    },
    SubmissionStatus.UNDER_REVIEW: {
        SubmissionStatus.DRAFT,
        SubmissionStatus.APPROVED,
        SubmissionStatus.REJECTED,
        SubmissionStatus.ARCHIVED,
    },
    SubmissionStatus.APPROVED: {
        SubmissionStatus.SCHEDULED,
        SubmissionStatus.ARCHIVED,
    },
    SubmissionStatus.REJECTED: {SubmissionStatus.ARCHIVED},
    SubmissionStatus.SCHEDULED: {SubmissionStatus.ARCHIVED},
    SubmissionStatus.ARCHIVED: set(),
}


class InvalidStatusTransition(ValueError):
    pass


def transition_submission(submission, target_status: SubmissionStatus) -> None:
    try:
        current_status = SubmissionStatus(submission.status)
        target_status = SubmissionStatus(target_status)
    except ValueError as error:
        raise InvalidStatusTransition(str(error)) from error

    if target_status not in ALLOWED_TRANSITIONS[current_status]:
        raise InvalidStatusTransition(
            f"Cannot transition submission from {current_status.value} "
            f"to {target_status.value}"
        )
    submission.status = target_status.value
