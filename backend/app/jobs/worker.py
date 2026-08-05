import argparse
import asyncio
from hashlib import sha256
import logging
import socket
from datetime import datetime, timedelta, timezone
from time import sleep
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ai.dependencies import get_embedding_provider
from app.ai.indexing.chunks import ChunkIndexingService
from app.ai.explanations import process_explanation_run
from app.ai.generation.ollama_explainer import OllamaExplanationProvider
from app.ai.interfaces import EmbeddingProvider
from app.database import SessionLocal
from app.config import get_settings
from app.email.factory import get_email_provider
from app.models import (
    AIInferenceRun,
    BackgroundJob,
    OutboxEvent,
    ParliamentaryRecord,
    WorkerHeartbeat,
)
from app.notifications.service import NotificationService, StatusChangeNotifier
from app.jobs.queue import queue_snapshot
from app.observability.metrics import update_queue_metrics
from app.services.archiving import archive_ended_session_records
from app.similarity.duplicate_detection import build_similarity_text

logger = logging.getLogger(__name__)

LOCK_TIMEOUT = timedelta(minutes=5)
MAX_BACKOFF_SECONDS = 3600


def record_worker_heartbeat(
    db: Session,
    *,
    worker_id: str,
    now: datetime | None = None,
) -> None:
    observed_at = now or datetime.now(timezone.utc)
    statement = (
        insert(WorkerHeartbeat)
        .values(
            worker_id=worker_id,
            status="running",
            last_seen_at=observed_at,
            details={"hostname": socket.gethostname()},
        )
        .on_conflict_do_update(
            index_elements=["worker_id"],
            set_={
                "status": "running",
                "last_seen_at": observed_at,
                "metadata": {"hostname": socket.gethostname()},
            },
        )
    )
    db.execute(statement)


def claim_jobs(
    db: Session,
    *,
    worker_id: str,
    limit: int = 10,
    now: datetime | None = None,
    lock_timeout: timedelta = LOCK_TIMEOUT,
) -> list[BackgroundJob]:
    current_time = now or datetime.now(timezone.utc)
    claimable = or_(
        and_(
            BackgroundJob.status.in_(("pending", "retry")),
            BackgroundJob.next_attempt_at <= current_time,
        ),
        and_(
            BackgroundJob.status == "running",
            BackgroundJob.lock_expires_at < current_time,
        ),
    )
    jobs = list(
        db.scalars(
            select(BackgroundJob)
            .where(claimable)
            .order_by(BackgroundJob.next_attempt_at, BackgroundJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        ).all()
    )
    for job in jobs:
        job.status = "running"
        job.attempt_count += 1
        job.locked_at = current_time
        job.lock_expires_at = current_time + lock_timeout
        job.locked_by = worker_id
        job.last_error = None
    db.flush()
    return jobs


def complete_job(job: BackgroundJob, *, now: datetime | None = None) -> None:
    current_time = now or datetime.now(timezone.utc)
    job.status = "completed"
    job.completed_at = current_time
    job.updated_at = current_time
    job.locked_at = None
    job.lock_expires_at = None
    job.locked_by = None


def fail_job(
    job: BackgroundJob,
    error: Exception,
    *,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(timezone.utc)
    job.last_error = str(error)[:2000]
    job.updated_at = current_time
    job.locked_at = None
    job.lock_expires_at = None
    job.locked_by = None
    if job.attempt_count >= job.max_attempts:
        job.status = "dead_letter"
        logger.error(
            "background job %s moved to dead_letter after %d attempts: %s",
            job.id,
            job.attempt_count,
            job.last_error,
        )
        return
    job.status = "retry"
    delay = min(2**job.attempt_count, MAX_BACKOFF_SECONDS)
    job.next_attempt_at = current_time + timedelta(seconds=delay)


def _run_embedding_job(
    db: Session,
    job: BackgroundJob,
    provider: EmbeddingProvider,
) -> None:
    record_id = UUID(job.payload["record_id"])
    record = db.get(ParliamentaryRecord, record_id)
    if record is None:
        return
    text = build_similarity_text(record.subject, record.full_text)
    expected_hash = job.payload.get("content_hash")
    if expected_hash and sha256(text.encode("utf-8")).hexdigest() != expected_hash:
        # A newer edit superseded this request; its own transaction enqueues a
        # versioned job, so the stale job can complete without overwriting it.
        return
    if job.job_type != "index_record_chunks" and not (
        record.embedding is not None and record.embedding_model == provider.model_name
    ):
        vector = provider.embed_query(text)
        if len(vector) != provider.dimension:
            raise RuntimeError(
                f"embedding dimension mismatch: expected {provider.dimension}, got {len(vector)}"
            )
        record.embedding = vector
        record.embedding_model = provider.model_name

    settings = get_settings()
    ChunkIndexingService(
        db,
        provider,
        max_chars=settings.ai_chunk_max_chars,
        overlap_chars=settings.ai_chunk_overlap_chars,
        preprocessing_version=settings.ai_preprocessing_version,
    ).index_record(record)


def _run_notification_job(
    job: BackgroundJob,
    notifier: StatusChangeNotifier,
) -> None:
    payload = job.payload
    sent = asyncio.run(
        notifier.notify_status_change(
            recipient=payload["recipient"],
            record_id=UUID(payload["record_id"]),
            item_type=payload["item_type"],
            subject=payload["subject"],
            old_status=payload["old_status"],
            new_status=payload["new_status"],
        )
    )
    if not sent:
        raise RuntimeError("notification provider did not accept the message")


def run_job(
    db: Session,
    job: BackgroundJob,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    notifier: StatusChangeNotifier | None = None,
    explanation_provider=None,
) -> None:
    if job.job_type in {"embed_record", "reindex_record", "index_record_chunks"}:
        _run_embedding_job(db, job, embedding_provider or get_embedding_provider())
    elif job.job_type == "notification":
        _run_notification_job(
            job,
            notifier or NotificationService(get_email_provider()),
        )
    elif job.job_type == "archive_records":
        archive_ended_session_records(db)
    elif job.job_type == "generate_explanation":
        run = db.get(AIInferenceRun, UUID(job.payload["run_id"]))
        if run is None:
            return
        process_explanation_run(
            db,
            run,
            provider=(
                explanation_provider
                or OllamaExplanationProvider(get_settings())
            ),
        )
    else:
        raise ValueError(f"unsupported background job type: {job.job_type}")


def process_claimed_job(
    job_id: UUID,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    notifier: StatusChangeNotifier | None = None,
    explanation_provider=None,
) -> bool:
    with SessionLocal() as db:
        job = db.get(BackgroundJob, job_id)
        if job is None or job.status != "running":
            return False
        try:
            run_job(
                db,
                job,
                embedding_provider=embedding_provider,
                notifier=notifier,
                explanation_provider=explanation_provider,
            )
            complete_job(job)
            for event in db.scalars(
                select(OutboxEvent).where(OutboxEvent.job_id == job.id)
            ):
                event.status = "published"
                event.published_at = job.completed_at
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            job = db.get(BackgroundJob, job_id)
            if job is None:
                return False
            fail_job(job, exc)
            db.commit()
            logger.warning("background job %s failed: %s", job_id, exc)
            return False


def run_once(*, worker_id: str, limit: int = 10) -> int:
    with SessionLocal() as db:
        record_worker_heartbeat(db, worker_id=worker_id)
        jobs = claim_jobs(db, worker_id=worker_id, limit=limit)
        ids = [job.id for job in jobs]
        db.commit()
    for job_id in ids:
        process_claimed_job(job_id)
    with SessionLocal() as db:
        update_queue_metrics(queue_snapshot(db))
    return len(ids)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run durable NAZ background jobs")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--worker-id", default=socket.gethostname())
    args = parser.parse_args(argv)
    while True:
        processed = run_once(worker_id=args.worker_id, limit=args.batch_size)
        if args.once:
            return
        if processed == 0:
            sleep(max(0.1, args.poll_seconds))


if __name__ == "__main__":
    main()
