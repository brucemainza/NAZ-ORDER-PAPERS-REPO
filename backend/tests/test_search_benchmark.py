from datetime import date
from uuid import uuid4

import pytest

from app.ai.retrieval.benchmark import (
    benchmark_lexical_search,
    ensure_isolated_benchmark_database,
    percentile,
)
from app.models import ParliamentaryRecord, ParliamentarySession, User


def test_percentile_uses_nearest_rank_and_rejects_empty_samples():
    assert percentile([9.0, 1.0, 4.0, 2.0], 0.50) == 2.0
    assert percentile([9.0, 1.0, 4.0, 2.0], 0.95) == 9.0
    with pytest.raises(ValueError, match="at least one"):
        percentile([], 0.95)


def test_benchmark_requires_an_explicitly_isolated_database_name():
    ensure_isolated_benchmark_database(
        "postgresql+psycopg://user:secret@db/naz_live_verification"
    )
    with pytest.raises(ValueError, match="isolated"):
        ensure_isolated_benchmark_database(
            "postgresql+psycopg://user:secret@db/naz_production"
        )


def test_benchmark_exercises_real_postgres_retrieval(db_session):
    sitting = ParliamentarySession(
        code=f"BENCH-{uuid4()}",
        name="Benchmark session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    user = User(
        employee_id=f"BENCH-{uuid4()}",
        name="Benchmark user",
        role="Legacy",
        status="Active",
    )
    db_session.add_all([sitting, user])
    db_session.flush()
    for index in range(12):
        db_session.add(
            ParliamentaryRecord(
                item_type="Question",
                session_id=sitting.id,
                member=f"Member {index}",
                ministry="Ministry of Health",
                subject=f"Rural clinic medicine supply {index}",
                full_text="Maintain medicine supplies in rural clinics.",
                status="Approved",
            )
        )
    db_session.commit()

    result = benchmark_lexical_search(
        db_session,
        user,
        queries=["rural clinic medicine"],
        warmup_runs=1,
        measured_runs=3,
        result_limit=5,
        p95_budget_ms=3000,
    )

    assert result.mode == "postgres_lexical"
    assert result.samples == 3
    assert result.result_counts == [5, 5, 5]
    assert result.p95_ms <= result.max_ms
    assert result.passed is True
