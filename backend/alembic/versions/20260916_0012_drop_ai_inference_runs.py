"""Drop ai_inference_runs (qwen-based grounded explanation feature removed).

The project now uses embeddinggemma only; the local-LLM grounded
explanation feature (and its qwen dependency) has been removed, and
this table was only ever written to by that feature.

Revision ID: 20260916_0012
Revises: 20260805_0011
Create Date: 2026-09-16
"""

from alembic import op

revision = "20260916_0012"
down_revision = "20260805_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_inference_runs CASCADE")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_inference_runs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            run_type text NOT NULL,
            user_id uuid REFERENCES users(id) ON DELETE SET NULL,
            query_hash varchar(64),
            evidence_ids uuid[],
            prompt_version text,
            model text NOT NULL,
            model_digest text,
            request_metadata jsonb,
            result jsonb,
            outcome text NOT NULL,
            latency_ms integer,
            error text,
            cache_key text UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_inference_runs_run_type ON ai_inference_runs(run_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_inference_runs_query_hash ON ai_inference_runs(query_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_inference_runs_outcome ON ai_inference_runs(outcome)"
    )
