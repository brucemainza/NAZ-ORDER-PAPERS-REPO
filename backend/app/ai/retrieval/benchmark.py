from dataclasses import dataclass
from math import ceil
from time import perf_counter

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.ai.retrieval.lexical import PostgresLexicalRetriever
from app.ai.schemas import SimilaritySearchRequest


@dataclass(frozen=True, slots=True)
class SearchBenchmarkResult:
    mode: str
    samples: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    p95_budget_ms: float
    passed: bool
    result_counts: list[int]


def percentile(samples: list[float], quantile: float) -> float:
    if not samples:
        raise ValueError("at least one latency sample is required")
    if not 0 < quantile <= 1:
        raise ValueError("quantile must be greater than zero and at most one")
    ordered = sorted(samples)
    return ordered[max(0, ceil(quantile * len(ordered)) - 1)]


def ensure_isolated_benchmark_database(database_url: str) -> None:
    database_name = (make_url(database_url).database or "").casefold()
    if not any(
        marker in database_name
        for marker in ("test", "benchmark", "verification")
    ):
        raise ValueError(
            "search benchmarks require an isolated test, benchmark, or "
            "verification database"
        )


def benchmark_lexical_search(
    db: Session,
    user,
    *,
    queries: list[str],
    warmup_runs: int,
    measured_runs: int,
    result_limit: int,
    p95_budget_ms: float,
) -> SearchBenchmarkResult:
    if not queries or any(not query.strip() for query in queries):
        raise ValueError("at least one non-empty benchmark query is required")
    if warmup_runs < 0 or measured_runs < 1:
        raise ValueError("benchmark run counts are invalid")
    retriever = PostgresLexicalRetriever(db, user)

    for index in range(warmup_runs):
        retriever.search_page(
            SimilaritySearchRequest(
                query_text=queries[index % len(queries)],
                limit=result_limit,
            ),
            limit=result_limit,
            offset=0,
        )

    latencies: list[float] = []
    result_counts: list[int] = []
    for index in range(measured_runs):
        request = SimilaritySearchRequest(
            query_text=queries[index % len(queries)],
            limit=result_limit,
        )
        started = perf_counter()
        matches, _ = retriever.search_page(
            request,
            limit=result_limit,
            offset=0,
        )
        latencies.append((perf_counter() - started) * 1000)
        result_counts.append(len(matches))

    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)
    p99 = percentile(latencies, 0.99)
    return SearchBenchmarkResult(
        mode="postgres_lexical",
        samples=len(latencies),
        p50_ms=round(p50, 3),
        p95_ms=round(p95, 3),
        p99_ms=round(p99, 3),
        max_ms=round(max(latencies), 3),
        p95_budget_ms=float(p95_budget_ms),
        passed=p95 <= p95_budget_ms,
        result_counts=result_counts,
    )
