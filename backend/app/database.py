from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine_options = {
    "echo": False,
    "hide_parameters": True,
    "pool_pre_ping": True,
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
    "pool_recycle": settings.db_pool_recycle_seconds,
    "pool_timeout": settings.db_pool_timeout,
}
if settings.database_url.startswith("postgresql"):
    engine_options["connect_args"] = {
        "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
    }
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
