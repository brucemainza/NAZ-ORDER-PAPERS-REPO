"""Run Alembic migrations under a PostgreSQL advisory lock."""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, create_engine, text

from app.config import get_settings


# Stable signed bigint derived from the application name. It serializes schema
# changes without blocking unrelated advisory-lock users.
MIGRATION_LOCK_ID = 5_549_176_001


class MigrationAlreadyRunning(RuntimeError):
    pass


@contextmanager
def migration_lock(connection: Connection) -> Iterator[None]:
    acquired = connection.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"),
        {"lock_id": MIGRATION_LOCK_ID},
    ).scalar_one()
    if not acquired:
        raise MigrationAlreadyRunning("another schema migration is already running")
    try:
        yield
    finally:
        connection.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": MIGRATION_LOCK_ID},
        )


def upgrade_to_head(database_url: str | None = None) -> None:
    url = database_url or get_settings().database_url
    engine = create_engine(url, pool_pre_ping=True)
    config = Config(Path(__file__).parents[1] / "alembic.ini")
    try:
        # Alembic uses the supplied connection's existing transaction. Using
        # engine.begin() ensures successful migrations are committed when the
        # context exits; engine.connect() would roll them back on close.
        with engine.begin() as connection:
            with migration_lock(connection):
                config.attributes["connection"] = connection
                config.attributes["database_url"] = url
                command.upgrade(config, "head")
    finally:
        engine.dispose()


if __name__ == "__main__":
    upgrade_to_head()
