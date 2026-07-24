"""Add pgvector embeddings to parliamentary records.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from alembic import op

revision = "20260724_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        ALTER TABLE parliamentary_records
        ADD COLUMN IF NOT EXISTS embedding vector(384)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_parliamentary_records_embedding
        ON parliamentary_records
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_parliamentary_records_embedding")
    op.execute(
        """
        ALTER TABLE parliamentary_records
        DROP COLUMN IF EXISTS embedding
        """
    )
