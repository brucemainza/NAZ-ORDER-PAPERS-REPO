"""Create the complete pre-AI production schema for fresh installations.

Revision ID: 20260701_0000
Revises:
Create Date: 2026-08-05

Existing installations already stamped at a later revision do not execute this
baseline. Fresh installations start here and then apply the historical,
idempotent migrations in order.
"""

from alembic import op

revision = "20260701_0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text UNIQUE NOT NULL,
            description text NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text UNIQUE NOT NULL,
            description text
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            employee_id text UNIQUE NOT NULL,
            name text NOT NULL,
            email text,
            role text NOT NULL,
            status text NOT NULL CHECK (status IN ('Active', 'Inactive')),
            password_hash text,
            failed_login_attempts integer NOT NULL DEFAULT 0,
            locked_at timestamptz,
            last_login_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, role_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            jti text UNIQUE NOT NULL,
            issued_at timestamptz NOT NULL,
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            ip_address text,
            user_agent text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS parliamentary_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text UNIQUE NOT NULL,
            name text NOT NULL,
            start_date date NOT NULL,
            end_date date NOT NULL,
            status text NOT NULL CHECK (status IN ('Active', 'Closed', 'Upcoming')),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS parliamentary_records (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            item_type text NOT NULL CHECK (item_type IN ('Question', 'Motion')),
            session_id uuid NOT NULL REFERENCES parliamentary_sessions(id),
            member text NOT NULL,
            ministry text,
            answer_type text CHECK (answer_type IN ('Oral', 'Written')),
            subject text NOT NULL,
            full_text text NOT NULL,
            status text NOT NULL DEFAULT 'Draft'
                CONSTRAINT parliamentary_records_status_check CHECK (
                    status IN ('Draft', 'Submitted', 'Under Review', 'Approved',
                    'Rejected', 'Scheduled', 'Answered', 'Discussed', 'Archived')
                ),
            submitted_by uuid REFERENCES users(id),
            sitting_date date,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS related_item_links (
            record_id uuid NOT NULL REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            related_record_id uuid NOT NULL REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            PRIMARY KEY (record_id, related_record_id),
            CONSTRAINT related_item_links_distinct_records CHECK (record_id <> related_record_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_responses (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            record_id uuid UNIQUE NOT NULL REFERENCES parliamentary_records(id) ON DELETE CASCADE,
            response_text text NOT NULL,
            response_date date NOT NULL,
            recorded_by uuid NOT NULL REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_logs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid REFERENCES users(id),
            query_text text NOT NULL,
            session_id uuid REFERENCES parliamentary_sessions(id),
            top_result_ids uuid[],
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_decisions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            record_id uuid NOT NULL REFERENCES parliamentary_records(id),
            similar_record_id uuid REFERENCES parliamentary_records(id),
            decision text NOT NULL CHECK (
                decision IN ('Clear (New)', 'Duplicate', 'Substantially Similar')
            ),
            is_duplicate boolean NOT NULL DEFAULT false,
            notes text,
            reviewer_id uuid REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_decisions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            record_id uuid NOT NULL REFERENCES parliamentary_records(id),
            action text NOT NULL CHECK (
                action IN ('Approve', 'Reject', 'Request Changes')
            ),
            notes text,
            reviewer_id uuid NOT NULL REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid REFERENCES users(id),
            action text NOT NULL,
            item_reference text,
            entity_type text,
            entity_id text,
            details text,
            ip_address text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_records_session_id "
        "ON parliamentary_records(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_records_item_type "
        "ON parliamentary_records(item_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_sessions_jti ON user_sessions(jti)"
    )


def downgrade() -> None:
    raise RuntimeError(
        "The production baseline is intentionally irreversible; restore a backup instead."
    )
