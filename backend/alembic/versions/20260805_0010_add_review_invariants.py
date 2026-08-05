"""Enforce review decision relationship invariants.

Revision ID: 20260805_0010
Revises: 20260805_0009
Create Date: 2026-08-05
"""

from alembic import op

revision = "20260805_0010"
down_revision = "20260805_0009"
branch_labels = None
depends_on = None


def _validate_when_existing_rows_are_compatible(constraint: str, predicate: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM review_decisions WHERE NOT ({predicate})
            ) THEN
                ALTER TABLE review_decisions VALIDATE CONSTRAINT {constraint};
            END IF;
        END
        $$
        """
    )


def _add_constraint_when_missing(constraint: str, predicate: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{constraint}'
                  AND conrelid = 'review_decisions'::regclass
            ) THEN
                ALTER TABLE review_decisions
                ADD CONSTRAINT {constraint}
                CHECK ({predicate}) NOT VALID;
            END IF;
        END
        $$
        """
    )


def upgrade() -> None:
    relationship_predicate = """
        (decision = 'Clear (New)' AND similar_record_id IS NULL
            AND is_duplicate = false)
        OR
        (decision IN ('Duplicate', 'Substantially Similar')
            AND similar_record_id IS NOT NULL AND is_duplicate = true)
    """
    distinct_predicate = "similar_record_id IS NULL OR record_id <> similar_record_id"
    _add_constraint_when_missing(
        "review_decisions_relationship_check",
        relationship_predicate,
    )
    _add_constraint_when_missing(
        "review_decisions_distinct_records",
        distinct_predicate,
    )
    _validate_when_existing_rows_are_compatible(
        "review_decisions_relationship_check",
        relationship_predicate,
    )
    _validate_when_existing_rows_are_compatible(
        "review_decisions_distinct_records",
        distinct_predicate,
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE review_decisions "
        "DROP CONSTRAINT IF EXISTS review_decisions_distinct_records"
    )
    op.execute(
        "ALTER TABLE review_decisions "
        "DROP CONSTRAINT IF EXISTS review_decisions_relationship_check"
    )
