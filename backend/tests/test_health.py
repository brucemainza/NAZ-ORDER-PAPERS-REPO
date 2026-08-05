from app.main import app
from app.routers.health import get_readiness_probe


class FakeReadinessProbe:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def snapshot(self):
        return self._snapshot


def _snapshot(*, ready=True, ai_status="healthy", worker_status="healthy"):
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": {"status": "healthy" if ready else "unavailable"},
            "schema": {
                "status": "current" if ready else "unknown",
                "current_revision": "20260805_0011",
                "expected_revision": "20260805_0011",
            },
            "ai": {"status": ai_status, "required": False},
            "worker": {"status": worker_status, "required": False},
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


def test_ollama_failure_marks_ai_degraded_without_failing_core_readiness(client):
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe(
        _snapshot(ready=True, ai_status="degraded", worker_status="stale")
    )

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["ai"] == {
        "status": "degraded",
        "required": False,
    }
    assert response.json()["checks"]["worker"]["required"] is False
