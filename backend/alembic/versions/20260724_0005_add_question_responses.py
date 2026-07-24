"""Add recorded responses for questions.

Revision ID: 20260724_0005
Revises: 20260724_0004
Create Date: 2026-07-24
"""

from alembic import op

revision = "20260724_0005"
down_revision = "20260724_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_responses (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            record_id uuid UNIQUE NOT NULL
                REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            response_text text NOT NULL,
            response_date date NOT NULL,
            recorded_by uuid NOT NULL REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS question_responses")
