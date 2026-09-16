from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.db_compat import seed_runtime_authorization
from app.observability.logging import configure_structured_logging
from app.observability.middleware import RequestObservabilityMiddleware
from app.ai import router as ai_router
from app.routers import (
    audit,
    auth,
    health,
    notifications,
    order_papers,
    records,
    reports,
    responses,
    reviews,
    roles,
    search,
    scheduling,
    session_reports,
    sessions,
    submissions,
    users,
    workflow_reviews,
)
from app.services.archiving import archive_ended_session_records

settings = get_settings()
configure_structured_logging(level=settings.log_level, enabled=settings.log_json)


def startup() -> None:
    seed_runtime_authorization()
    with SessionLocal() as db:
        archive_ended_session_records(db)
        db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    startup()
    yield


app = FastAPI(
    title="NAZ Order Papers API",
    description="Backend API for parliamentary question and motion similarity retrieval.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestObservabilityMiddleware)

app.include_router(health.router)
app.include_router(notifications.router)
app.include_router(sessions.router)
app.include_router(order_papers.router)
app.include_router(records.router)
app.include_router(search.router)
app.include_router(scheduling.router)
app.include_router(session_reports.router)
app.include_router(submissions.router)
app.include_router(reviews.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(responses.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(workflow_reviews.router)
app.include_router(ai_router.router)
