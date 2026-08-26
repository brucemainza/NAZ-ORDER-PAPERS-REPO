"""Update parliamentary record embedding dimension to 768 and add model tracking.

Revision ID: 20260730_0006
Revises: 20260724_0005
Create Date: 2026-07-30
"""

from alembic import op

revision = "20260730_0006"
down_revision = "20260724_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing embeddings were produced by a feature-hash generator and must be
    # regenerated with the new embedding model anyway, so dropping the column is
    # safe and avoids pgvector's restriction on altering vector dimensions.
    op.execute("DROP INDEX IF EXISTS idx_parliamentary_records_embedding")
    op.execute("ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS embedding")
    op.execute(
        """
        ALTER TABLE parliamentary_records
        ADD COLUMN IF NOT EXISTS embedding vector(768)
        """
    )
    op.execute(
        """
        ALTER TABLE parliamentary_records
        ADD COLUMN IF NOT EXISTS embedding_model text
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
    op.execute("ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS embedding_model")
    op.execute("ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS embedding")
    op.execute(
        """
        ALTER TABLE parliamentary_records
        ADD COLUMN embedding vector(384)
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
