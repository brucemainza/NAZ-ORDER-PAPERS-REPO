from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS = Counter(
    "naz_http_requests_total",
    "Total HTTP requests handled by the API.",
    ("method", "route", "status"),
    registry=REGISTRY,
)
HTTP_FAILURES = Counter(
    "naz_http_request_failures_total",
    "Total HTTP responses with a server-error status.",
    ("method", "route", "status"),
    registry=REGISTRY,
)
HTTP_REQUEST_DURATION = Histogram(
    "naz_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    registry=REGISTRY,
)
HTTP_IN_PROGRESS = Gauge(
    "naz_http_requests_in_progress",
    "HTTP requests currently being handled.",
    ("method",),
    registry=REGISTRY,
    multiprocess_mode="livesum",
)
AI_MODEL_CALLS = Counter(
    "naz_ai_model_calls_total",
    "Local AI model calls by operation and outcome.",
    ("operation", "outcome"),
    registry=REGISTRY,
)
AI_DEGRADED_SEARCHES = Counter(
    "naz_ai_degraded_searches_total",
    "Searches completed with lexical-only degradation.",
    registry=REGISTRY,
)
BACKGROUND_QUEUE_DEPTH = Gauge(
    "naz_background_queue_depth",
    "Background jobs by current state.",
    ("status",),
    registry=REGISTRY,
    multiprocess_mode="livesum",
)
AI_INDEX_COVERAGE = Gauge(
    "naz_ai_index_coverage_percent",
    "Percentage of eligible records with compatible chunk embeddings.",
    registry=REGISTRY,
    multiprocess_mode="livesum",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


def update_queue_metrics(snapshot) -> None:
    for status in ("pending", "running", "retry", "dead_letter"):
        BACKGROUND_QUEUE_DEPTH.labels(status=status).set(getattr(snapshot, status))
