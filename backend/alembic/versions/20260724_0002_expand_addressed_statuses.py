"""Allow answered and discussed parliamentary records.

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from alembic import op

revision = "20260724_0002"
down_revision = "20260724_0001"
branch_labels = None
depends_on = None

STATUS_CHECK = """
status IN (
    'Draft', 'Submitted', 'Under Review', 'Approved', 'Rejected',
    'Scheduled', 'Answered', 'Discussed', 'Archived'
)
"""


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE parliamentary_records
        DROP CONSTRAINT IF EXISTS parliamentary_records_status_check
        """
    )
    op.execute(
        """
        UPDATE parliamentary_records
        SET status = 'Archived'
        WHERE status = 'Historical'
        """
    )
    op.execute(
        f"""
        ALTER TABLE parliamentary_records
        ADD CONSTRAINT parliamentary_records_status_check
        CHECK ({STATUS_CHECK})
        """
    )


def downgrade() -> None:
    # Deliberately non-destructive: narrowing the check could strand valid
    # Answered/Discussed production rows. A reviewed data migration is required.
    pass
