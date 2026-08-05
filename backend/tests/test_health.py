import httpx

from app.config import Settings
from app.main import app
from app.routers.health import get_readiness_probe
from app.services.readiness import ReadinessProbe


class FakeReadinessProbe:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def snapshot(self):
        return self._snapshot


def _snapshot(
    *,
    ready=True,
    ai_status="healthy",
    worker_status="healthy",
    dead_letter=0,
):
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": {"status": "healthy" if ready else "unavailable"},
            "schema": {
                "status": "current" if ready else "unknown",
                "current_revision": "20260805_0011",
                "expected_revision": "20260805_0011",
            },
            "ai": {"status": ai_status, "required": True},
            "worker": {"status": worker_status, "required": False},
            "queue": {
                "status": "unhealthy" if dead_letter else "healthy",
                "dead_letter": dead_letter,
            },
        },
    }


def test_liveness_and_legacy_health_work_without_dependencies(client):
    class ExplodingProbe:
        def snapshot(self):
            raise RuntimeError("dependencies are down")

    app.dependency_overrides[get_readiness_probe] = lambda: ExplodingProbe()

    live = client.get("/livez")
    legacy = client.get("/health")

    assert live.status_code == legacy.status_code == 200
    assert live.json() == legacy.json() == {"status": "ok"}


def test_readiness_reports_database_or_schema_failure(client):
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe(
        _snapshot(ready=False, ai_status="degraded", worker_status="unavailable")
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"]["status"] == "unavailable"


def test_ollama_failure_fails_readiness_with_clear_required_check(client):
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe(
        _snapshot(ready=False, ai_status="unavailable", worker_status="stale")
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["ai"] == {
        "status": "unavailable",
        "required": True,
    }
    assert response.json()["checks"]["worker"]["required"] is False


def test_dead_letter_jobs_fail_readiness_and_are_visible(client):
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe(
        _snapshot(ready=False, dead_letter=2)
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["checks"]["queue"] == {
        "status": "unhealthy",
        "dead_letter": 2,
    }


def test_readiness_probe_surfaces_ollama_connection_failure(monkeypatch):
    settings = Settings()
    settings.ollama_base_url = "http://ollama:11434"

    def connection_refused(*_args, **_kwargs):
        request = httpx.Request("GET", "http://ollama:11434/api/tags")
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(httpx, "get", connection_refused)
    probe = ReadinessProbe(db_engine=None, settings=settings)

    assert probe._ai() == {
        "status": "unavailable",
        "required": True,
        "base_url": "http://ollama:11434",
        "error": "Ollama is unreachable",
    }
