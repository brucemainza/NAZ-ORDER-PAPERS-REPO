from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import re

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

BEARER_PATTERN = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+")
JWT_PATTERN = re.compile(
    r"\b[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)
CREDENTIAL_URL_PATTERN = re.compile(r"(://[^\s:/]+:)[^@\s]+(@)")
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(authorization|token|password|secret|prompt|full_text|query_text)"
    r"\s*[=:]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


def redact(value: str) -> str:
    redacted = BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    redacted = JWT_PATTERN.sub("[REDACTED]", redacted)
    redacted = CREDENTIAL_URL_PATTERN.sub(r"\1[REDACTED]\2", redacted)
    return SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        redacted,
    )


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get()
        return True


class RedactingJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }
        for field in ("method", "path", "route", "status", "duration_ms"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging(*, level: str = "INFO", enabled: bool = True) -> None:
    if not enabled:
        return
    root = logging.getLogger()
    if any(getattr(handler, "_naz_json_handler", False) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler._naz_json_handler = True
    handler.setFormatter(RedactingJsonFormatter())
    handler.addFilter(RequestContextFilter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
