from datetime import date, datetime, timezone
from uuid import uuid4

from app.ai.retrieval.lexical import PostgresLexicalRetriever
from app.ai.schemas import SimilaritySearchRequest
from app.models import ParliamentaryRecord, ParliamentarySession, User
from app.schemas.search import SearchRequest


def _session(db):
    session = ParliamentarySession(
        code=f"FTS-{uuid4()}",
        name="FTS test session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db.add(session)
    db.flush()
    return session


def _record(db, session, *, subject, full_text, status="Approved", member="Member"):
    record = ParliamentaryRecord(
        item_type="Question",
        session_id=session.id,
        member=member,
        ministry="Ministry of Water",
        answer_type="Oral",
        subject=subject,
        full_text=full_text,
        status=status,
        created_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )
    db.add(record)
    db.flush()
    return record


def test_hybrid_is_the_default_search_mode():
    assert SearchRequest(query_text="rural water").mode == "hybrid"


def test_differently_ordered_terms_retrieve_the_same_record(db_session):
    session = _session(db_session)
    target = _record(
        db_session,
        session,
        subject="Rural water programme",
        full_text="Borehole construction and clean water access.",
    )
    user = User(
        employee_id=f"FTS-{uuid4()}", name="Search User", role="Legacy", status="Active"
    )
    db_session.add(user)
    db_session.commit()
    retriever = PostgresLexicalRetriever(db_session, user)

    first = retriever.search(SimilaritySearchRequest(query_text="rural water"), 10)
    second = retriever.search(SimilaritySearchRequest(query_text="water rural"), 10)

    assert [match.record_id for match in first] == [target.id]
    assert [match.record_id for match in second] == [target.id]


def test_long_full_text_does_not_remove_lexical_candidate(db_session):
    session = _session(db_session)
    target = _record(
        db_session,
        session,
        subject="Infrastructure update",
        full_text=("routine parliamentary background " * 5000)
        + " uniqueaquifer rehabilitation schedule",
    )
    user = User(
        employee_id=f"FTS-{uuid4()}", name="Search User", role="Legacy", status="Active"
    )
    db_session.add(user)
    db_session.commit()

    matches = PostgresLexicalRetriever(db_session, user).search(
        SimilaritySearchRequest(query_text="uniqueaquifer"),
        5,
    )

    assert [match.record_id for match in matches] == [target.id]


def test_visibility_and_filters_apply_before_ranking(db_session):
    session = _session(db_session)
    visible = _record(
        db_session,
        session,
        subject="Solar irrigation",
        full_text="Solar pumps for farms",
        member="Hon. Visible",
    )
    _record(
        db_session,
        session,
        subject="Solar irrigation draft",
        full_text="Solar pumps for farms with many additional solar references",
        status="Draft",
        member="Hon. Hidden",
    )
    user = User(
        employee_id=f"FTS-{uuid4()}", name="Search User", role="Legacy", status="Active"
    )
    db_session.add(user)
    db_session.commit()

    matches = PostgresLexicalRetriever(db_session, user).search(
        SimilaritySearchRequest(
            query_text="solar irrigation",
            session_id=session.id,
            item_type="Question",
            status="Approved",
            member="visible",
        ),
        10,
    )

    assert [match.record_id for match in matches] == [visible.id]


def test_pagination_is_stable_and_ranked_in_postgres(db_session, monkeypatch):
    session = _session(db_session)
    records = [
        _record(
            db_session,
            session,
            subject=f"Transport corridor {index}",
            full_text="transport corridor rehabilitation",
        )
        for index in range(6)
    ]
    user = User(
        employee_id=f"FTS-{uuid4()}", name="Search User", role="Legacy", status="Active"
    )
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr(
        "app.retrieval.bm25.rank_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Python corpus ranking must not run")
        ),
    )
    retriever = PostgresLexicalRetriever(db_session, user)
    request = SimilaritySearchRequest(query_text="transport corridor")

    first_page, first_total = retriever.search_page(request, limit=2, offset=0)
    second_page, second_total = retriever.search_page(request, limit=2, offset=2)

    assert first_total == second_total == len(records)
    assert len(first_page) == len(second_page) == 2
    assert {item.record_id for item in first_page}.isdisjoint(
        {item.record_id for item in second_page}
    )
