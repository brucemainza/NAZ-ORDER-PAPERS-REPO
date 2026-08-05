import inspect
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, text

from app.main import startup
from scripts.migrate import MIGRATION_LOCK_ID, migration_lock


ADMIN_URL = "postgresql://naz_user:naz_password@localhost:5433/postgres"
APP_URL_PREFIX = "postgresql+psycopg://naz_user:naz_password@localhost:5433/"


@contextmanager
def isolated_database():
    name = f"naz_migration_{os.getpid()}_{uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{name}"')
    try:
        yield f"{APP_URL_PREFIX}{name}"
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            connection.execute(f'DROP DATABASE "{name}"')


def alembic_config(database_url: str) -> Config:
    path = Path(__file__).parents[1] / "alembic.ini"
    config = Config(path)
    config.attributes["database_url"] = database_url
    return config


def test_fresh_database_upgrades_to_complete_head():
    with isolated_database() as database_url:
        command.upgrade(alembic_config(database_url), "head")

        engine = create_engine(database_url)
        try:
            tables = set(sqlalchemy_inspect(engine).get_table_names())
            with engine.connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
        finally:
            engine.dispose()

    assert revision == "20260805_0011"
    assert {
        "parliamentary_records",
        "background_jobs",
        "outbox_events",
        "record_chunks",
        "ai_inference_runs",
        "idempotency_keys",
        "worker_heartbeats",
    }.issubset(tables)


def test_database_at_0006_upgrades_without_losing_records():
    with isolated_database() as database_url:
        config = alembic_config(database_url)
        command.upgrade(config, "20260730_0006")
        engine = create_engine(database_url)
        record_id = uuid4()
        session_id = uuid4()
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO parliamentary_sessions "
                        "(id, code, name, start_date, end_date, status) "
                        "VALUES (:id, 'TEST', 'Test session', '2026-01-01', "
                        "'2026-12-31', 'Active')"
                    ),
                    {"id": session_id},
                )
                connection.execute(
                    text(
                        "INSERT INTO parliamentary_records "
                        "(id, item_type, session_id, member, subject, full_text, status) "
                        "VALUES (:id, 'Question', :session_id, 'Member', "
                        "'Water supply', 'When will works begin?', 'Submitted')"
                    ),
                    {"id": record_id, "session_id": session_id},
                )

            command.upgrade(config, "head")
            with engine.connect() as connection:
                persisted = connection.execute(
                    text(
                        "SELECT subject, normalized_hash FROM parliamentary_records "
                        "WHERE id = :id"
                    ),
                    {"id": record_id},
                ).one()
        finally:
            engine.dispose()

    assert persisted.subject == "Water supply"
    assert len(persisted.normalized_hash) == 64


def test_application_startup_performs_no_schema_ddl():
    source = inspect.getsource(startup).casefold()
    assert "ensure_runtime_schema" not in source
    assert "create table" not in source
    assert "alter table" not in source


def test_alembic_is_the_only_checked_in_schema_manager():
    backend_root = Path(__file__).parents[1]

    assert not (backend_root / "db" / "schema.sql").exists()


def test_migration_lock_rejects_a_concurrent_runner():
    first = create_engine(os.environ["DATABASE_URL"])
    second = create_engine(os.environ["DATABASE_URL"])
    try:
        with first.connect() as first_connection:
            with migration_lock(first_connection):
                with second.connect() as second_connection:
                    acquired = second_connection.execute(
                        text("SELECT pg_try_advisory_lock(:lock_id)"),
                        {"lock_id": MIGRATION_LOCK_ID},
                    ).scalar_one()
                    assert acquired is False
    finally:
        first.dispose()
        second.dispose()
