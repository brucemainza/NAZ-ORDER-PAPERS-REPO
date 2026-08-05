"""Add worker heartbeat reporting.

Revision ID: 20260805_0011
Revises: 20260805_0010
Create Date: 2026-08-05
"""

from alembic import op

revision = "20260805_0011"
down_revision = "20260805_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_heartbeats (
            worker_id text PRIMARY KEY,
            status text NOT NULL DEFAULT 'running',
            metadata jsonb,
            started_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_worker_heartbeats_last_seen_at "
        "ON worker_heartbeats (last_seen_at)"
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
