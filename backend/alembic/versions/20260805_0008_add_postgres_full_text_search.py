"""Add maintained weighted PostgreSQL full-text search.

Revision ID: 20260805_0008
Revises: 20260805_0007
Create Date: 2026-08-05
"""

from alembic import op

revision = "20260805_0008"
down_revision = "20260805_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE parliamentary_records
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(subject, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(full_text, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(member, '')), 'C') ||
            setweight(to_tsvector('english', coalesce(ministry, '')), 'C')
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_records_search_vector "
        "ON parliamentary_records USING gin(search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_parliamentary_records_search_vector")
    op.execute(
        "ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS search_vector"
    )
