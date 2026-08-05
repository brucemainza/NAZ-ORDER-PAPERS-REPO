from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.jobs.queue import enqueue_job, enqueue_outbox_job, queue_snapshot
from app.jobs.worker import claim_jobs, fail_job, process_claimed_job, run_job
from app.models import (
    BackgroundJob,
    OutboxEvent,
    ParliamentaryRecord,
    ParliamentarySession,
    WorkerHeartbeat,
)
from app.jobs.worker import record_worker_heartbeat


def _session(db):
    session = ParliamentarySession(
        code=f"JOBS-{uuid4()}",
        name="Jobs test session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db.add(session)
    db.flush()
    return session


def _record(db):
    parliamentary_session = _session(db)
    record = ParliamentaryRecord(
        item_type="Question",
        session_id=parliamentary_session.id,
        member="Member",
        ministry="Health",
        answer_type="Oral",
        subject="Rural clinics",
        full_text="When will additional clinical staff be deployed?",
        status="Under Review",
    )
    db.add(record)
    db.flush()
    return record


def test_job_and_outbox_event_commit_with_domain_record(db_session):
    record = _record(db_session)
    job = enqueue_outbox_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(record.id), "content_hash": "abc"},
        deduplication_key=f"embed:{record.id}:abc:model-v1",
        aggregate_type="parliamentary_record",
        aggregate_id=str(record.id),
        event_type="record.indexing_requested",
    )
    db_session.commit()

    persisted_job = db_session.get(BackgroundJob, job.id)
    event = db_session.scalar(select(OutboxEvent))
    assert persisted_job is not None
    assert event is not None
    assert event.job_id == persisted_job.id


def test_rolled_back_domain_transaction_leaves_no_job(db_session):
    record = _record(db_session)
    enqueue_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(record.id)},
        deduplication_key=f"embed:{record.id}:rollback",
    )
    db_session.rollback()

    assert db_session.scalar(select(BackgroundJob)) is None
    assert db_session.get(ParliamentaryRecord, record.id) is None


def test_two_workers_cannot_claim_the_same_job(db_session):
    enqueue_job(
        db_session,
        job_type="archive_records",
        payload={},
        deduplication_key=f"archive:{uuid4()}",
    )
    db_session.commit()

    first = Session(engine)
    second = Session(engine)
    try:
        first_claim = claim_jobs(first, worker_id="worker-a", limit=1)
        second_claim = claim_jobs(second, worker_id="worker-b", limit=1)
        assert len(first_claim) == 1
        assert second_claim == []
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()


def test_interrupted_job_is_reclaimed_after_lock_expiry(db_session):
    job = enqueue_job(
        db_session,
        job_type="archive_records",
        payload={},
        deduplication_key=f"archive:{uuid4()}",
    )
    job.status = "running"
    job.locked_by = "dead-worker"
    job.lock_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    claimed = claim_jobs(db_session, worker_id="replacement", limit=1)

    assert [item.id for item in claimed] == [job.id]
    assert claimed[0].locked_by == "replacement"
    assert claimed[0].attempt_count == 1


def test_repeated_enqueue_is_idempotent(db_session):
    key = f"embed:{uuid4()}:same-version"
    first = enqueue_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(uuid4())},
        deduplication_key=key,
    )
    second = enqueue_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(uuid4())},
        deduplication_key=key,
    )
    db_session.commit()

    assert first.id == second.id
    assert db_session.query(BackgroundJob).count() == 1


def test_failed_jobs_back_off_and_eventually_dead_letter(db_session):
    job = enqueue_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(uuid4())},
        deduplication_key=f"embed:{uuid4()}:failure",
        max_attempts=2,
    )
    db_session.commit()
    initial_time = datetime(2026, 8, 5, tzinfo=timezone.utc)

    job.attempt_count = 1
    fail_job(job, RuntimeError("offline"), now=initial_time)
    assert job.status == "retry"
    assert job.next_attempt_at == initial_time + timedelta(seconds=2)

    job.attempt_count = 2
    fail_job(job, RuntimeError("still offline"), now=initial_time)
    assert job.status == "dead_letter"
    assert job.last_error == "still offline"


def test_embedding_handler_is_idempotent_for_same_model(db_session):
    record = _record(db_session)
    job = enqueue_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(record.id)},
        deduplication_key=f"embed:{record.id}:model-v1",
    )
    db_session.commit()

    class Provider:
        model_name = "model-v1"
        model_digest = "sha256:model-v1"
        dimension = 768

        def __init__(self):
            self.calls = 0

        def embed_query(self, _text):
            self.calls += 1
            return [0.25] * 768

        def embed_documents(self, texts):
            return [[0.25] * 768 for _ in texts]

    provider = Provider()
    run_job(db_session, job, embedding_provider=provider)
    run_job(db_session, job, embedding_provider=provider)

    assert provider.calls == 1
    assert record.embedding_model == "model-v1"


def test_dimension_mismatch_marks_indexing_job_retryable(db_session):
    record = _record(db_session)
    job = enqueue_job(
        db_session,
        job_type="embed_record",
        payload={"record_id": str(record.id)},
        deduplication_key=f"embed:{record.id}:bad-dimension",
    )
    db_session.commit()
    claimed = claim_jobs(db_session, worker_id="worker-a", limit=1)
    db_session.commit()

    class WrongDimensionProvider:
        model_name = "broken-model"
        model_digest = "sha256:broken"
        dimension = 768

        def embed_query(self, _text):
            return [0.1] * 12

    completed = process_claimed_job(
        claimed[0].id,
        embedding_provider=WrongDimensionProvider(),
    )
    db_session.expire_all()
    failed = db_session.get(BackgroundJob, job.id)

    assert completed is False
    assert failed.status == "retry"
    assert "dimension mismatch" in failed.last_error.casefold()


def test_queue_snapshot_reports_actionable_depth(db_session):
    enqueue_job(
        db_session,
        job_type="archive_records",
        payload={},
        deduplication_key=f"archive:{uuid4()}",
    )
    db_session.commit()

    snapshot = queue_snapshot(db_session)

    assert snapshot.pending == 1
    assert snapshot.dead_letter == 0
    assert snapshot.oldest_pending_seconds >= 0


def test_worker_heartbeat_is_upserted_for_readiness(db_session):
    observed_at = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)

    record_worker_heartbeat(
        db_session,
        worker_id="worker-health-test",
        now=observed_at,
    )
    record_worker_heartbeat(
        db_session,
        worker_id="worker-health-test",
        now=observed_at + timedelta(seconds=5),
    )
    db_session.commit()

    heartbeat = db_session.get(WorkerHeartbeat, "worker-health-test")
    assert heartbeat.last_seen_at == observed_at + timedelta(seconds=5)
    assert db_session.query(WorkerHeartbeat).count() == 1
