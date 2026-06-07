from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db_compat import ensure_runtime_schema
from app.routers import audit, auth, health, records, reports, reviews, search, sessions, submissions

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
app.include_router(records.router)
app.include_router(search.router)
app.include_router(submissions.router)
app.include_router(reviews.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(auth.router)


@app.on_event("startup")
def startup() -> None:
    ensure_runtime_schema()
