"""End-to-end tests for the hybrid RAG pipeline.

These tests exercise the full AISimilarityService orchestrator with real
PostgreSQL records and chunks but a deterministic fake embedding provider so
they do not depend on a running Ollama instance.
"""

import hashlib
from datetime import date
from uuid import uuid4

from sqlalchemy import select

from app.ai.indexing.chunks import ChunkIndexingService
from app.ai.schemas import SimilaritySearchRequest
from app.ai.service import AISimilarityService
from app.config import Settings
from app.models import ParliamentaryRecord, ParliamentarySession, RecordChunk, User


class _FakeEmbeddingProvider:
    """Deterministic feature-hash embedding provider for tests.

    Uses BLAKE2b feature hashing so semantically similar texts (same tokens)
    produce similar vectors and different texts produce different vectors.
    """

    model_name = "fake-embedding-model"
    model_digest = "sha256:test"
    dimension = 768

    def embed_query(self, text: str) -> list[float]:
        return self._vector_for(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]

    def _vector_for(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = text.casefold().split()
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.blake2b(
                token.encode("utf-8"),
                digest_size=16,
                person=b"naz-embed-test",
            ).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            vector[index] += 1.0
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


def _active_session(db):
    session = ParliamentarySession(
        code=f"RAG-{uuid4()}",
        name="RAG test session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db.add(session)
    db.flush()
    return session


def _approved_record(db, session, subject, full_text, item_type="Question"):
    record = ParliamentaryRecord(
        item_type=item_type,
        session_id=session.id,
        member="Hon. Test Member",
        ministry="Ministry of Tests",
        answer_type="Written",
        subject=subject,
        full_text=full_text,
        status="Approved",
    )
    db.add(record)
    db.flush()
    return record


def _index_record(db, record, provider):
    service = ChunkIndexingService(
        db,
        provider,
        max_chars=300,
        overlap_chars=50,
        preprocessing_version="rag-test-v1",
    )
    service.index_record(record)
    db.flush()


def _user():
    return User(
        employee_id=f"RAG-{uuid4()}",
        name="RAG Tester",
        role="Viewer",
        status="Active",
    )


def _service(db, provider):
    settings = Settings()
    settings.ai_preprocessing_version = "rag-test-v1"
    return AISimilarityService(
        db,
        _user(),
        settings,
        embedding_provider=provider,
    )


def test_hybrid_search_combines_lexical_and_semantic_results(db_session):
    """Both retrievers should contribute candidates to the fused result list."""
    session = _active_session(db_session)
    provider = _FakeEmbeddingProvider()

    # Lexical-only match: contains the exact query terms.
    lexical_match = _approved_record(
        db_session,
        session,
        subject="Rural water access report",
        full_text="This report covers rural water access in detail.",
    )
    # Semantic match: shares vocabulary with the query but not all exact terms.
    semantic_match = _approved_record(
        db_session,
        session,
        subject="Borehole sanitation programme",
        full_text="Rural communities need improved borehole and sanitation access.",
    )
    _index_record(db_session, lexical_match, provider)
    _index_record(db_session, semantic_match, provider)
    db_session.commit()

    response = _service(db_session, provider).search(
        SimilaritySearchRequest(query_text="rural water access", limit=5)
    )

    assert response.retrieval_mode == "hybrid"
    assert not response.degraded
    assert response.total_lexical >= 1
    assert response.total_semantic == 2
    ids = {match.record_id for match in response.results}
    assert lexical_match.id in ids
    assert semantic_match.id in ids


def test_hybrid_search_record_matching_both_modalities_ranks_first(db_session):
    """A record that matches both lexical and semantic should outrank single-modality matches."""
    session = _active_session(db_session)
    provider = _FakeEmbeddingProvider()

    only_lexical = _approved_record(
        db_session,
        session,
        subject="Rural water access",
        full_text="Exact phrase match but nothing else.",
    )
    only_semantic = _approved_record(
        db_session,
        session,
        subject="Borehole programme",
        full_text="Rural communities need improved borehole and sanitation access.",
    )
    both = _approved_record(
        db_session,
        session,
        subject="Rural water access and boreholes",
        full_text="Rural water access programme including borehole construction.",
    )
    _index_record(db_session, only_lexical, provider)
    _index_record(db_session, only_semantic, provider)
    _index_record(db_session, both, provider)
    db_session.commit()

    response = _service(db_session, provider).search(
        SimilaritySearchRequest(query_text="rural water access", limit=5)
    )

    assert response.results[0].record_id == both.id


def test_hybrid_search_degrades_to_lexical_when_embedding_provider_fails(
    db_session,
):
    session = _active_session(db_session)

    class _FailingProvider(_FakeEmbeddingProvider):
        def embed_query(self, _text):
            raise RuntimeError("embedding service down")

    provider = _FailingProvider()
    record = _approved_record(
        db_session,
        session,
        subject="Rural water access",
        full_text="Improve rural water access and boreholes.",
    )
    _index_record(db_session, record, provider)
    db_session.commit()

    response = _service(db_session, provider).search(
        SimilaritySearchRequest(query_text="rural water", limit=5)
    )

    assert response.retrieval_mode == "lexical"
    assert response.degraded is True
    assert "Semantic retrieval is temporarily unavailable." in response.warnings
    assert any(match.record_id == record.id for match in response.results)


def test_hybrid_search_filters_by_session_and_item_type(db_session):
    session_a = _active_session(db_session)
    session_b = _active_session(db_session)
    provider = _FakeEmbeddingProvider()

    record_a = _approved_record(
        db_session,
        session_a,
        subject="Water in session A",
        full_text="Rural water access programme.",
    )
    record_b = _approved_record(
        db_session,
        session_b,
        subject="Water in session B",
        full_text="Rural water access programme.",
        item_type="Motion",
    )
    _index_record(db_session, record_a, provider)
    _index_record(db_session, record_b, provider)
    db_session.commit()

    response = _service(db_session, provider).search(
        SimilaritySearchRequest(
            query_text="rural water",
            session_id=session_a.id,
            limit=5,
        )
    )
    assert all(match.record_id == record_a.id for match in response.results)

    response = _service(db_session, provider).search(
        SimilaritySearchRequest(
            query_text="rural water",
            item_type="Motion",
            limit=5,
        )
    )
    assert all(match.record_id == record_b.id for match in response.results)


def test_hybrid_search_pagination_is_stable(db_session):
    session = _active_session(db_session)
    provider = _FakeEmbeddingProvider()

    records = []
    for index in range(5):
        record = _approved_record(
            db_session,
            session,
            subject=f"Water topic {index}",
            full_text=f"Rural water access programme number {index}.",
        )
        _index_record(db_session, record, provider)
        records.append(record)
    db_session.commit()

    page_1 = _service(db_session, provider).search(
        SimilaritySearchRequest(query_text="rural water", limit=2, offset=0)
    )
    page_2 = _service(db_session, provider).search(
        SimilaritySearchRequest(query_text="rural water", limit=2, offset=2)
    )

    assert len(page_1.results) == 2
    assert len(page_2.results) == 2
    assert {r.record_id for r in page_1.results}.isdisjoint(
        {r.record_id for r in page_2.results}
    )


def test_semantic_retriever_collapses_multiple_chunks_per_record(db_session):
    """Only the best chunk per record should contribute to semantic results."""
    session = _active_session(db_session)
    provider = _FakeEmbeddingProvider()

    record = _approved_record(
        db_session,
        session,
        subject="Water access",
        full_text=" ".join(
            [f"paragraph {index} about rural water access" for index in range(20)]
        ),
    )
    _index_record(db_session, record, provider)
    db_session.commit()

    chunk_count = db_session.scalar(
        select(RecordChunk.id).where(RecordChunk.record_id == record.id)
    )
    assert chunk_count is not None

    response = _service(db_session, provider).search(
        SimilaritySearchRequest(query_text="rural water access", limit=5)
    )

    semantic_ids = [m.record_id for m in response.results if m.semantic_rank]
    assert record.id in semantic_ids
    assert semantic_ids.count(record.id) == 1
