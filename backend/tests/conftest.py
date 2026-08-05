import os

import psycopg
import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_NAME = "naz_order_papers_test"
TEST_DATABASE_URL = (
    "postgresql+psycopg://naz_user:naz_password@localhost:5433/"
    f"{TEST_DATABASE_NAME}"
)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["UPLOAD_MALWARE_SCAN_REQUIRED"] = "false"

with psycopg.connect(
    "postgresql://naz_user:naz_password@localhost:5433/postgres",
    autocommit=True,
) as connection:
    exists = connection.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (TEST_DATABASE_NAME,),
    ).fetchone()
    if not exists:
        connection.execute(f'CREATE DATABASE "{TEST_DATABASE_NAME}"')

from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app import models as _models  # noqa: E402, F401
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
