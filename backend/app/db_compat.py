"""Compatibility data seeding after Alembic has established the schema.

This module deliberately performs no DDL. Schema changes belong exclusively to
Alembic migrations.
"""

from app.database import SessionLocal
from app.services.permissions import assign_legacy_roles, seed_default_roles


def seed_runtime_authorization() -> None:
    with SessionLocal() as session:
        seed_default_roles(session)
        assign_legacy_roles(session)
        session.commit()
