from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import BackgroundJob, OutboxEvent


@dataclass(frozen=True)
class QueueSnapshot:
    pending: int
    running: int
    retry: int
    dead_letter: int
    oldest_pending_seconds: float


def enqueue_job(
    db: Session,
    *,
    job_type: str,
    payload: dict,
    deduplication_key: str,
    max_attempts: int = 5,
) -> BackgroundJob:
    """Enqueue once without committing the caller's domain transaction."""

    job_id = uuid4()
    statement = (
        insert(BackgroundJob)
        .values(
            id=job_id,
            job_type=job_type,
            payload=payload,
            deduplication_key=deduplication_key,
            max_attempts=max_attempts,
        )
        .on_conflict_do_nothing(index_elements=["deduplication_key"])
        .returning(BackgroundJob.id)
    )
    inserted_id = db.execute(statement).scalar_one_or_none()
    resolved_id = inserted_id or db.scalar(
        select(BackgroundJob.id).where(
            BackgroundJob.deduplication_key == deduplication_key
        )
    )
    if resolved_id is None:  # pragma: no cover - defensive database invariant
        raise RuntimeError("could not resolve enqueued background job")
    return db.get(BackgroundJob, resolved_id)


def enqueue_outbox_job(
    db: Session,
    *,
    job_type: str,
    payload: dict,
    deduplication_key: str,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    max_attempts: int = 5,
) -> BackgroundJob:
    job = enqueue_job(
        db,
        job_type=job_type,
        payload=payload,
        deduplication_key=deduplication_key,
        max_attempts=max_attempts,
    )
    existing_event = db.scalar(
        select(OutboxEvent).where(
            OutboxEvent.job_id == job.id,
            OutboxEvent.event_type == event_type,
        )
    )
    if existing_event is None:
        db.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
                job_id=job.id,
            )
        )
    return job


def queue_snapshot(db: Session) -> QueueSnapshot:
    counts = dict(
        db.execute(
            select(BackgroundJob.status, func.count(BackgroundJob.id)).group_by(
                BackgroundJob.status
            )
        ).all()
    )
    oldest = db.scalar(
        select(func.min(BackgroundJob.created_at)).where(
            BackgroundJob.status.in_(("pending", "retry"))
        )
    )
    age = 0.0
    if oldest is not None:
        now = datetime.now(timezone.utc)
        age = max(0.0, (now - oldest).total_seconds())
    return QueueSnapshot(
        pending=counts.get("pending", 0),
        running=counts.get("running", 0),
        retry=counts.get("retry", 0),
        dead_letter=counts.get("dead_letter", 0),
        oldest_pending_seconds=age,
    )
