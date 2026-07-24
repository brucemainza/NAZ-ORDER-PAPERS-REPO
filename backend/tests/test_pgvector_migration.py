import importlib.util
from pathlib import Path

from sqlalchemy import text

from app.database import engine


def test_pgvector_alembic_migration_is_additive_and_idempotent():
    assert importlib.util.find_spec("alembic") is not None, (
        "Alembic must be installed for versioned schema migrations"
    )

    from alembic import command
    from alembic.config import Config

    config_path = Path(__file__).parents[1] / "alembic.ini"
    assert config_path.exists(), "Alembic configuration is missing"
    config = Config(config_path)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    with engine.connect() as connection:
        extension_exists = connection.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar_one()
        embedding_column = connection.execute(
            text(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_name = 'parliamentary_records'
                  AND column_name = 'embedding'
                """
            )
        ).scalar_one()

    assert extension_exists is True
    assert embedding_column == "vector"
