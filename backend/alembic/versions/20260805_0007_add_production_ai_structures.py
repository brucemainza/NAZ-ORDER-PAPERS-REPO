"""Add durable jobs, chunk indexing, inference audit, and idempotency storage.

Revision ID: 20260805_0007
Revises: 20260730_0006
Create Date: 2026-08-05
"""

from alembic import op

revision = "20260805_0007"
down_revision = "20260730_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE parliamentary_records ADD COLUMN IF NOT EXISTS normalized_hash varchar(64)"
    )
    op.execute(
        "ALTER TABLE parliamentary_records ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1"
    )
    op.execute(
        "ALTER TABLE parliamentary_records ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parliamentary_records_normalized_hash "
        "ON parliamentary_records(normalized_hash)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS background_jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            job_type text NOT NULL,
            deduplication_key text UNIQUE NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            status text NOT NULL DEFAULT 'pending'
                CONSTRAINT background_jobs_status_check CHECK (
                    status IN ('pending', 'running', 'retry', 'completed', 'dead_letter')
                ),
            attempt_count integer NOT NULL DEFAULT 0,
            max_attempts integer NOT NULL DEFAULT 5,
            next_attempt_at timestamptz NOT NULL DEFAULT now(),
            locked_at timestamptz,
            lock_expires_at timestamptz,
            locked_by text,
            last_error text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_background_jobs_job_type ON background_jobs(job_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_background_jobs_next_attempt_at ON background_jobs(next_attempt_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_background_jobs_claim "
        "ON background_jobs(status, next_attempt_at, lock_expires_at)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            aggregate_type text NOT NULL,
            aggregate_id text NOT NULL,
            event_type text NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            status text NOT NULL DEFAULT 'pending',
            job_id uuid REFERENCES background_jobs(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            published_at timestamptz
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_aggregate_id ON outbox_events(aggregate_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_event_type ON outbox_events(event_type)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS record_chunks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            record_id uuid NOT NULL REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            chunk_text text NOT NULL,
            content_hash varchar(64) NOT NULL,
            embedding vector(768),
            embedding_model text NOT NULL,
            model_digest text NOT NULL,
            dimension integer NOT NULL,
            preprocessing_version text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_record_chunks_version UNIQUE (
                record_id, chunk_index, content_hash, embedding_model,
                model_digest, preprocessing_version
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_chunks_record_id ON record_chunks(record_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_chunks_content_hash ON record_chunks(content_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_record_chunks_embedding_hnsw "
        "ON record_chunks USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL"
    )
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
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            scope text NOT NULL,
            key text NOT NULL,
            request_hash varchar(64) NOT NULL,
            response_status integer,
            response_body jsonb,
            resource_type text,
            resource_id text,
            user_id uuid REFERENCES users(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz,
            CONSTRAINT uq_idempotency_scope_key UNIQUE (scope, key)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS idempotency_keys")
    op.execute("DROP TABLE IF EXISTS ai_inference_runs")
    op.execute("DROP TABLE IF EXISTS record_chunks")
    op.execute("DROP TABLE IF EXISTS outbox_events")
    op.execute("DROP TABLE IF EXISTS background_jobs")
    op.execute("DROP INDEX IF EXISTS ix_parliamentary_records_normalized_hash")
    op.execute("ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS version")
    op.execute("ALTER TABLE parliamentary_records DROP COLUMN IF EXISTS normalized_hash")
