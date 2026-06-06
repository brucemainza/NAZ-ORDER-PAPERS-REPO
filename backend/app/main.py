from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, health, records, search, sessions

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
app.include_router(auth.router)