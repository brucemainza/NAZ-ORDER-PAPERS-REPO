"""Benchmark PostgreSQL lexical retrieval against a production-sized corpus.

The command inserts synthetic records inside one transaction and always rolls
that transaction back. It still requires an explicitly isolated database because
the temporary write load and ANALYZE are inappropriate for a live database.

Usage:
    DATABASE_URL=postgresql+psycopg://.../naz_search_benchmark \
      python -m scripts.benchmark_search --allow-isolated-write-benchmark
"""

import argparse
from dataclasses import asdict
from datetime import date
import json
from uuid import uuid4

from sqlalchemy import func, select, text

from app.ai.retrieval.benchmark import (
    benchmark_lexical_search,
    ensure_isolated_benchmark_database,
)
from app.config import get_settings
from app.database import SessionLocal
from app.models import ParliamentaryRecord, ParliamentarySession, User


BENCHMARK_QUERIES = [
    "rural clinic medicine supply",
    "secondary school classroom construction",
    "feeder road bridge maintenance",
    "solar irrigation farming programme",
    "youth skills employment training",
    "clean water borehole rehabilitation",
    "electricity grid connection expansion",
    "public finance budget oversight",
]


def seed_records(db, *, record_count: int, sitting_id, seed_prefix: str) -> None:
    db.execute(
        text(
            """
            WITH generated AS (
                SELECT
                    series,
                    CASE series % 8
                        WHEN 0 THEN 'rural clinic medicine supply'
                        WHEN 1 THEN 'secondary school classroom construction'
                        WHEN 2 THEN 'feeder road bridge maintenance'
                        WHEN 3 THEN 'solar irrigation farming programme'
                        WHEN 4 THEN 'youth skills employment training'
                        WHEN 5 THEN 'clean water borehole rehabilitation'
                        WHEN 6 THEN 'electricity grid connection expansion'
                        ELSE 'public finance budget oversight'
                    END AS topic
                FROM generate_series(1, :record_count) AS series
            )
            INSERT INTO parliamentary_records (
                id,
                item_type,
                session_id,
                member,
                ministry,
                subject,
                full_text,
                status,
                version
            )
            SELECT
                md5(:seed_prefix || series::text)::uuid,
                'Question',
                :sitting_id,
                'Member ' || (series % 250)::text,
                'Ministry ' || (series % 24)::text,
                initcap(topic) || ' ' || series::text,
                'The member requests an implementation update concerning ' ||
                    topic || ' for constituency ' || (series % 180)::text || '.',
                'Approved',
                1
            FROM generated
            """
        ),
        {
            "record_count": record_count,
            "seed_prefix": seed_prefix,
            "sitting_id": sitting_id,
        },
    )


def run_benchmark(
    *,
    record_count: int,
    warmup_runs: int,
    measured_runs: int,
    result_limit: int,
    p95_budget_ms: float,
) -> dict:
    settings = get_settings()
    ensure_isolated_benchmark_database(settings.database_url)
    seed_prefix = f"naz-search-benchmark-{uuid4()}-"

    with SessionLocal() as db:
        transaction = db.begin()
        try:
            user = User(
                employee_id=f"BENCH-{uuid4()}",
                name="Search benchmark",
                role="Benchmark",
                status="Active",
            )
            sitting = ParliamentarySession(
                code=f"BENCH-{uuid4()}",
                name="Search benchmark",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="Active",
            )
            db.add_all([user, sitting])
            db.flush()
            seed_records(
                db,
                record_count=record_count,
                sitting_id=sitting.id,
                seed_prefix=seed_prefix,
            )
            db.execute(text("ANALYZE parliamentary_records"))
            corpus_size = db.scalar(select(func.count(ParliamentaryRecord.id))) or 0
            result = benchmark_lexical_search(
                db,
                user,
                queries=BENCHMARK_QUERIES,
                warmup_runs=warmup_runs,
                measured_runs=measured_runs,
                result_limit=result_limit,
                p95_budget_ms=p95_budget_ms,
            )
            return {
                **asdict(result),
                "seeded_records": record_count,
                "corpus_size": int(corpus_size),
                "queries": BENCHMARK_QUERIES,
                "transaction_rolled_back": True,
            }
        finally:
            transaction.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark real PostgreSQL FTS and ranking on an isolated database"
    )
    parser.add_argument("--records", type=int, default=100_000)
    parser.add_argument("--warmup-runs", type=int, default=8)
    parser.add_argument("--measured-runs", type=int, default=40)
    parser.add_argument("--result-limit", type=int, default=20)
    parser.add_argument("--p95-budget-ms", type=float, default=3000)
    parser.add_argument("--allow-isolated-write-benchmark", action="store_true")
    args = parser.parse_args()
    if not args.allow_isolated_write_benchmark:
        parser.error("--allow-isolated-write-benchmark is required")
    if args.records < 1_000:
        parser.error("--records must be at least 1000")
    result = run_benchmark(
        record_count=args.records,
        warmup_runs=args.warmup_runs,
        measured_runs=args.measured_runs,
        result_limit=args.result_limit,
        p95_budget_ms=args.p95_budget_ms,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
