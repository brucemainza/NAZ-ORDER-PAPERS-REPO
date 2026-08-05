import json
import logging

from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.observability.logging import RedactingJsonFormatter


def test_database_pool_and_statement_timeout_are_configured():
    settings = get_settings()

    assert engine.pool._pre_ping is True
    assert engine.pool.size() == settings.db_pool_size
    assert engine.pool._max_overflow == settings.db_max_overflow
    assert engine.pool._timeout == settings.db_pool_timeout
    with engine.connect() as connection:
        statement_timeout_ms = connection.execute(
            text(
                "SELECT EXTRACT(epoch FROM "
                "current_setting('statement_timeout')::interval) * 1000"
            )
        ).scalar_one()
    assert int(statement_timeout_ms) == settings.db_statement_timeout_ms


def test_request_ids_are_returned_and_added_to_request_logs(client, caplog):
    caplog.set_level(logging.INFO, logger="app.observability.http")

    response = client.get("/livez", headers={"X-Request-ID": "request-test-001"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-test-001"
    records = [record for record in caplog.records if record.name == "app.observability.http"]
    assert records
    assert records[-1].request_id == "request-test-001"
    assert records[-1].path == "/livez"


def test_structured_logging_redacts_credentials_tokens_and_prompts():
    formatter = RedactingJsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=(
            "Authorization=Bearer abc.def.ghi password=hunter2 "
            "prompt=private-parliament-text full_text=secret-record"
        ),
        args=(),
        exc_info=None,
    )
    record.request_id = "redaction-test"

    rendered = formatter.format(record)
    payload = json.loads(rendered)

    assert payload["request_id"] == "redaction-test"
    assert "abc.def.ghi" not in rendered
    assert "hunter2" not in rendered
    assert "private-parliament-text" not in rendered
    assert "secret-record" not in rendered
    assert "[REDACTED]" in rendered


def test_prometheus_metrics_expose_request_latency_and_failures(client):
    client.get("/livez")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "naz_http_requests_total" in response.text
    assert "naz_http_request_duration_seconds" in response.text
    assert "naz_background_queue_depth" in response.text
