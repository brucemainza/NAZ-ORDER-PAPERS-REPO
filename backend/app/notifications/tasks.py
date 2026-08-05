"""Durably enqueue status notifications in the caller's transaction."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.jobs.queue import enqueue_outbox_job
from app.models import BackgroundJob


def enqueue_status_change_notification(
    db: Session,
    *,
    event_key: str,
    recipient: str | None,
    record_id: UUID,
    item_type: str,
    subject: str,
    old_status: str,
    new_status: str,
) -> BackgroundJob | None:
    if not recipient or old_status == new_status:
        return None
    payload = {
        "recipient": recipient,
        "record_id": str(record_id),
        "item_type": item_type,
        "subject": subject,
        "old_status": old_status,
        "new_status": new_status,
    }
    return enqueue_outbox_job(
        db,
        job_type="notification",
        payload=payload,
        deduplication_key=f"notification:{event_key}",
        aggregate_type="parliamentary_record",
        aggregate_id=str(record_id),
        event_type="notification.requested",
    )
