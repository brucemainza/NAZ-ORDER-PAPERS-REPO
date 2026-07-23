from sqlalchemy import or_

from app.models import ParliamentaryRecord, User


def restrict_draft_visibility(query, user: User):
    if user.has_permission("review_submission"):
        return query
    return query.where(
        or_(
            ParliamentaryRecord.status != "Draft",
            ParliamentaryRecord.submitted_by == user.id,
        )
    )


def can_view_record(record: ParliamentaryRecord, user: User) -> bool:
    return (
        record.status != "Draft"
        or record.submitted_by == user.id
        or user.has_permission("review_submission")
    )
