from sqlalchemy import text

from app.database import SessionLocal, engine
from app.services.permissions import assign_legacy_roles, seed_default_roles


def ensure_runtime_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text UNIQUE NOT NULL,
            description text NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS roles (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text UNIQUE NOT NULL,
            description text
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, role_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS workflow_decisions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            record_id uuid NOT NULL REFERENCES parliamentary_records(id),
            action text NOT NULL,
            notes text,
            reviewer_id uuid NOT NULL REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """,
        "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts integer NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_at timestamptz",
        "ALTER TABLE parliamentary_records ADD COLUMN IF NOT EXISTS answer_type text",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_type text",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_id text",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS details text",
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'audit_logs'
                  AND column_name = 'item_reference'
            ) THEN
                EXECUTE 'UPDATE audit_logs SET entity_id = item_reference WHERE entity_id IS NULL AND item_reference IS NOT NULL';
            END IF;
        END;
        $$
        """,
        "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS similar_record_id uuid REFERENCES parliamentary_records(id)",
        "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS decision text",
        "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS is_duplicate boolean NOT NULL DEFAULT false",
        "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS reviewer_id uuid REFERENCES users(id)",
        "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()",
        "DO $$\n        BEGIN\n            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'review_decisions' AND column_name = 'decided_by') THEN\n                EXECUTE 'UPDATE review_decisions SET reviewer_id = decided_by WHERE reviewer_id IS NULL AND decided_by IS NOT NULL';\n            END IF;\n        END;\n        $$",
        "DO $$\n        BEGIN\n            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'review_decisions' AND column_name = 'decided_at') THEN\n                EXECUTE 'UPDATE review_decisions SET created_at = decided_at WHERE created_at IS NULL AND decided_at IS NOT NULL';\n            END IF;\n        END;\n        $$",
        "UPDATE review_decisions SET decision = CASE WHEN is_duplicate THEN 'Duplicate' ELSE 'Clear (New)' END WHERE decision IS NULL",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    with SessionLocal() as session:
        seed_default_roles(session)
        assign_legacy_roles(session)
        session.commit()
