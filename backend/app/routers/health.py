from fastapi import APIRouter, Depends, Response, status

from app.services.readiness import ReadinessProbe, get_readiness_probe

router = APIRouter(tags=["health"])


@router.get("/livez")
@router.get("/health")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readiness(
    response: Response,
    probe: ReadinessProbe = Depends(get_readiness_probe),
) -> dict:
    snapshot = probe.snapshot()
    if snapshot["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return snapshot
