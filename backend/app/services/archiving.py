from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord, ParliamentarySession
from app.services.submission_status import (
    SubmissionStatus,
    transition_submission,
)


def archive_ended_session_records(
    db: Session,
    *,
    as_of: date | None = None,
) -> int:
    effective_date = as_of or date.today()
    records = db.scalars(
        select(ParliamentaryRecord)
        .join(ParliamentarySession)
        .where(
            ParliamentaryRecord.status != SubmissionStatus.ARCHIVED.value,
            or_(
                ParliamentarySession.end_date < effective_date,
                func.lower(ParliamentarySession.status) == "closed",
            ),
        )
    ).all()

    for record in records:
        transition_submission(record, SubmissionStatus.ARCHIVED)

    db.flush()
    return len(records)
