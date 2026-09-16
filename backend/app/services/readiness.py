from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
import httpx
from sqlalchemy import func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import engine
from app.jobs.queue import queue_snapshot
from app.models import WorkerHeartbeat


def expected_schema_revision() -> str:
    config = Config(Path(__file__).parents[2] / "alembic.ini")
    revision = ScriptDirectory.from_config(config).get_current_head()
    if revision is None:
        raise RuntimeError("Alembic has no schema head")
    return revision


class ReadinessProbe:
    def __init__(self, db_engine: Engine, settings: Settings) -> None:
        self._engine = db_engine
        self._settings = settings

    def _database_and_schema(self) -> tuple[dict, dict, bool]:
        expected = expected_schema_revision()
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return (
                {"status": "unavailable"},
                {
                    "status": "unknown",
                    "current_revision": None,
                    "expected_revision": expected,
                },
                False,
            )

        try:
            with self._engine.connect() as connection:
                current = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
        except Exception:
            current = None
        schema_current = current == expected
        return (
            {"status": "healthy"},
            {
                "status": "current" if schema_current else "outdated",
                "current_revision": current,
                "expected_revision": expected,
            },
            schema_current,
        )

    def _ai(self) -> dict:
        base_url = self._settings.ollama_base_url
        try:
            response = httpx.get(
                f"{base_url}/api/tags",
                timeout=self._settings.readiness_ai_timeout_seconds,
            )
            response.raise_for_status()
            models = {
                model.get("name") or model.get("model")
                for model in response.json().get("models", [])
            }
            required_models = {self._settings.ollama_embedding_model}
            missing_models = sorted(required_models - models)
            if missing_models:
                return {
                    "status": "unhealthy",
                    "required": self._settings.ai_required,
                    "base_url": base_url,
                    "error": "Required Ollama models are not loaded",
                    "missing_models": missing_models,
                }
            return {
                "status": "healthy",
                "required": self._settings.ai_required,
                "base_url": base_url,
                "models": sorted(required_models),
            }
        except Exception:
            return {
                "status": "unavailable",
                "required": self._settings.ai_required,
                "base_url": base_url,
                "error": "Ollama is unreachable",
            }

    def _worker_and_queue(self, database_healthy: bool) -> tuple[dict, dict]:
        if not database_healthy:
            return (
                {"status": "unknown", "required": False, "last_seen_at": None},
                {"status": "unknown"},
            )
        try:
            with Session(self._engine) as db:
                last_seen = db.scalar(func.max(WorkerHeartbeat.last_seen_at))
                queue = queue_snapshot(db)
        except Exception:
            return (
                {"status": "unknown", "required": False, "last_seen_at": None},
                {"status": "unknown"},
            )

        if last_seen is None:
            worker_status = "unavailable"
        else:
            age = (datetime.now(timezone.utc) - last_seen).total_seconds()
            worker_status = (
                "healthy"
                if age <= self._settings.worker_stale_seconds
                else "stale"
            )
        queue_status = "unhealthy" if queue.dead_letter else "healthy"
        return (
            {
                "status": worker_status,
                "required": False,
                "last_seen_at": last_seen.isoformat() if last_seen else None,
            },
            {
                "status": queue_status,
                "pending": queue.pending,
                "running": queue.running,
                "retry": queue.retry,
                "dead_letter": queue.dead_letter,
                "oldest_pending_seconds": round(queue.oldest_pending_seconds, 3),
            },
        )

    def snapshot(self) -> dict:
        database, schema, core_ready = self._database_and_schema()
        worker, queue = self._worker_and_queue(database["status"] == "healthy")
        ai = self._ai()
        ai_ready = ai["status"] == "healthy" or not self._settings.ai_required
        ready = (
            core_ready
            and ai_ready
            and queue.get("status") == "healthy"
        )
        return {
            "status": "ready" if ready else "not_ready",
            "checks": {
                "database": database,
                "schema": schema,
                "ai": ai,
                "worker": worker,
                "queue": queue,
            },
        }


def get_readiness_probe() -> ReadinessProbe:
    return ReadinessProbe(engine, get_settings())
