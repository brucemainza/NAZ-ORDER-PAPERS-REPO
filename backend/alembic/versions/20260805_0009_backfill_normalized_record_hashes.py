"""Backfill normalized exact-match hashes.

Revision ID: 20260805_0009
Revises: 20260805_0008
Create Date: 2026-08-05
"""

from alembic import op

revision = "20260805_0009"
down_revision = "20260805_0008"
branch_labels = None
depends_on = None

NORMALIZE = "trim(regexp_replace(lower(coalesce({column}, '')), '[^a-z0-9]+', ' ', 'g'))"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    item_type = NORMALIZE.format(column="item_type")
    subject = NORMALIZE.format(column="subject")
    full_text = NORMALIZE.format(column="full_text")
    op.execute(
        f"""
        UPDATE parliamentary_records
        SET normalized_hash = encode(
            digest(concat_ws(chr(31), {item_type}, {subject}, {full_text}), 'sha256'),
            'hex'
        )
        WHERE normalized_hash IS NULL
        """
    )


def downgrade() -> None:
    # Hashes are valid application data and are safe to retain.
    pass
