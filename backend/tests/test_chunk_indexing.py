from datetime import date
from uuid import uuid4

from sqlalchemy import func, select

from app.ai.indexing.chunks import (
    ChunkIndexingService,
    chunk_record,
    enqueue_chunk_backfill,
)
from app.ai.retrieval.semantic import PgVectorSemanticRetriever
from app.ai.schemas import SimilaritySearchRequest
from app.models import (
    BackgroundJob,
    ParliamentaryRecord,
    ParliamentarySession,
    RecordChunk,
    User,
)


class BatchProvider:
    model_name = "embedding-model"
    model_digest = "sha256:active"
    dimension = 768

    def __init__(self):
        self.calls = []

    def embed_documents(self, texts):
        self.calls.append(list(texts))
        return [[float(index + 1)] + [0.0] * 767 for index, _ in enumerate(texts)]


def _session(db):
    session = ParliamentarySession(
        code=f"CHUNKS-{uuid4()}",
        name="Chunk test session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db.add(session)
    db.flush()
    return session


def _record(db, session, subject="Water access", full_text=None):
    record = ParliamentaryRecord(
        item_type="Question",
        session_id=session.id,
        member="Member",
        ministry="Water",
        answer_type="Oral",
        subject=subject,
        full_text=full_text or ("rural borehole construction programme " * 100),
        status="Approved",
    )
    db.add(record)
    db.flush()
    return record


def test_long_records_create_deterministic_bounded_overlapping_chunks():
    text = " ".join(f"word{index}" for index in range(100))

    first = chunk_record("Water programme", text, max_chars=140, overlap_chars=30)
    second = chunk_record("Water programme", text, max_chars=140, overlap_chars=30)

    assert first == second
    assert len(first) > 1
    assert all(chunk.startswith("Subject: Water programme\n\n") for chunk in first)
    assert all(len(chunk) <= 140 for chunk in first)
    assert set(first[0].split()).intersection(first[1].split())


def test_unchanged_content_is_not_embedded_twice(db_session):
    record = _record(db_session, _session(db_session))
    provider = BatchProvider()
    service = ChunkIndexingService(
        db_session,
        provider,
        max_chars=300,
        overlap_chars=50,
        preprocessing_version="chunks-v1",
    )

    first_count = service.index_record(record)
    second_count = service.index_record(record)
    db_session.commit()

    assert first_count > 1
    assert second_count == 0
    assert len(provider.calls) == 1
    assert db_session.scalar(select(func.count(RecordChunk.id))) == first_count


def test_stale_model_vectors_are_excluded_and_chunk_hits_collapse(db_session):
    session = _session(db_session)
    active_record = _record(db_session, session, subject="Active vector")
    stale_record = _record(db_session, session, subject="Stale vector")
    db_session.add_all(
        [
            RecordChunk(
                record_id=active_record.id,
                chunk_index=0,
                chunk_text="active first",
                content_hash="a" * 64,
                embedding=[1.0] + [0.0] * 767,
                embedding_model="embedding-model",
                model_digest="sha256:active",
                dimension=768,
                preprocessing_version="chunks-v1",
            ),
            RecordChunk(
                record_id=active_record.id,
                chunk_index=1,
                chunk_text="active second",
                content_hash="b" * 64,
                embedding=[0.9, 0.1] + [0.0] * 766,
                embedding_model="embedding-model",
                model_digest="sha256:active",
                dimension=768,
                preprocessing_version="chunks-v1",
            ),
            RecordChunk(
                record_id=stale_record.id,
                chunk_index=0,
                chunk_text="stale",
                content_hash="c" * 64,
                embedding=[1.0] + [0.0] * 767,
                embedding_model="embedding-model",
                model_digest="sha256:stale",
                dimension=768,
                preprocessing_version="chunks-v1",
            ),
        ]
    )
    user = User(
        employee_id=f"CHUNK-{uuid4()}", name="Chunk User", role="Legacy", status="Active"
    )
    db_session.add(user)
    db_session.commit()

    matches = PgVectorSemanticRetriever(
        db_session,
        user,
        model="embedding-model",
        model_digest="sha256:active",
        dimension=768,
        preprocessing_version="chunks-v1",
    ).search(
        SimilaritySearchRequest(query_text="active"),
        [1.0] + [0.0] * 767,
        10,
    )

    assert [match.record_id for match in matches] == [active_record.id]
    assert matches[0].metadata["chunk_index"] == 0


def test_backfill_resumes_from_last_record_without_duplicate_jobs(db_session):
    session = _session(db_session)
    records = [_record(db_session, session, subject=f"Record {index}") for index in range(3)]
    db_session.commit()

    first = enqueue_chunk_backfill(
        db_session,
        model="embedding-model",
        model_digest="sha256:active",
        preprocessing_version="chunks-v1",
        limit=2,
    )
    db_session.commit()
    second = enqueue_chunk_backfill(
        db_session,
        model="embedding-model",
        model_digest="sha256:active",
        preprocessing_version="chunks-v1",
        after_id=first.next_cursor,
        limit=2,
    )
    db_session.commit()

    assert first.queued == 2
    assert second.queued == 1
    assert second.complete is True
    assert db_session.scalar(select(func.count(BackgroundJob.id))) == len(records)
