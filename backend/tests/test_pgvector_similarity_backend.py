import importlib
import importlib.util
from uuid import uuid4

from app.models import ParliamentaryRecord, ParliamentarySession
from app.similarity.embeddings import TokenHashEmbeddingGenerator


def _load_pgvector_backend():
    qualified_name = "app.similarity.pgvector_backend"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "Step 0 pgvector backend module has not been implemented"
    )
    return importlib.import_module(qualified_name).PgVectorSimilarityBackend


def _session():
    return ParliamentarySession(
        code=f"SIM-{uuid4()}",
        name="Similarity fixtures",
        start_date="2025-01-01",
        end_date="2025-12-31",
        status="Closed",
    )


def _record(session, generator, *, text, status="Archived", item_type="Question"):
    return ParliamentaryRecord(
        item_type=item_type,
        session=session,
        member="Test Member",
        ministry="Water Development",
        answer_type="Oral" if item_type == "Question" else None,
        subject=text,
        full_text=text,
        status=status,
        embedding=generator.embed(text),
    )


def test_pgvector_backend_returns_known_fixtures_in_similarity_order(db_session):
    backend_type = _load_pgvector_backend()
    generator = TokenHashEmbeddingGenerator()
    session = _session()
    query = "rural water boreholes access"
    identical = _record(session, generator, text=query)
    related = _record(
        session,
        generator,
        text="improve rural water access and boreholes",
    )
    unrelated = _record(
        session,
        generator,
        text="parliamentary cyber security budget",
    )
    db_session.add_all([identical, related, unrelated])
    db_session.commit()

    matches = backend_type(db_session, generator).find_similar(
        query,
        threshold=0.0,
        top_n=3,
    )

    assert [match.source_id for match in matches] == [
        identical.id,
        related.id,
        unrelated.id,
    ]
    assert matches[0].score == 1.0
    assert matches[0].score > matches[1].score > matches[2].score


def test_pgvector_backend_applies_threshold_filters_and_exclusions(db_session):
    backend_type = _load_pgvector_backend()
    generator = TokenHashEmbeddingGenerator()
    session = _session()
    query = "rural water boreholes access"
    exact = _record(session, generator, text=query, status="Archived")
    related = _record(
        session,
        generator,
        text="rural water boreholes access programme",
        status="Approved",
    )
    motion = _record(
        session,
        generator,
        text=query,
        status="Archived",
        item_type="Motion",
    )
    db_session.add_all([exact, related, motion])
    db_session.commit()

    matches = backend_type(db_session, generator).find_similar(
        query,
        threshold=0.8,
        top_n=5,
        exclude_ids=[exact.id],
        statuses=["Approved"],
        item_type="Question",
    )

    assert [match.source_id for match in matches] == [related.id]


def test_pgvector_backend_handles_empty_and_unrelated_inputs(db_session):
    backend_type = _load_pgvector_backend()
    generator = TokenHashEmbeddingGenerator()
    session = _session()
    record = _record(
        session,
        generator,
        text="rural water boreholes access",
    )
    db_session.add(record)
    db_session.commit()
    backend = backend_type(db_session, generator)

    assert backend.find_similar("", threshold=0.0, top_n=5) == []
    assert backend.find_similar(
        "international satellite launch programme",
        threshold=0.95,
        top_n=5,
    ) == []


def test_embedding_vector_is_persisted_with_the_configured_dimension(db_session):
    _load_pgvector_backend()
    generator = TokenHashEmbeddingGenerator()
    session = _session()
    record = _record(
        session,
        generator,
        text="rural water boreholes access",
    )
    db_session.add(record)
    db_session.commit()
    record_id = record.id
    db_session.expire_all()

    persisted = db_session.get(ParliamentaryRecord, record_id)

    assert persisted is not None
    assert len(persisted.embedding) == generator.dimension == 384
