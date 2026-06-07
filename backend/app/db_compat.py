from sqlalchemy import text

from app.database import engine


def ensure_runtime_schema() -> None:
    statements = [
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_type text",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_id text",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS details text",
        "UPDATE audit_logs SET entity_id = item_reference WHERE entity_id IS NULL AND item_reference IS NOT NULL",
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
