"""Add links from new records to related addressed records.

Revision ID: 20260724_0003
Revises: 20260724_0002
Create Date: 2026-07-24
"""

from alembic import op

revision = "20260724_0003"
down_revision = "20260724_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS related_item_links (
            record_id uuid NOT NULL
                REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            related_record_id uuid NOT NULL
                REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            PRIMARY KEY (record_id, related_record_id),
            CONSTRAINT related_item_links_distinct_records
                CHECK (record_id <> related_record_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS related_item_links")
