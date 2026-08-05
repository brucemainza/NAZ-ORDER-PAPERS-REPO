from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.db_compat import seed_runtime_authorization
from app.ai import router as ai_router
from app.routers import (
    audit,
    auth,
    health,
    order_papers,
    records,
    reports,
    responses,
    reviews,
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

app = FastAPI(
    title="NAZ Order Papers API",
    description="Backend API for parliamentary question and motion similarity retrieval.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
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
app.include_router(workflow_reviews.router)
app.include_router(ai_router.router)


@app.on_event("startup")
def startup() -> None:
    seed_runtime_authorization()
    with SessionLocal() as db:
        archive_ended_session_records(db)
        db.commit()
