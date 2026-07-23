# NAZ Order Papers Backend

FastAPI service for authentication, permission-based access control, parliamentary
submissions, review, scheduling, archive access, search, reporting, and audit.

## Local Development

PostgreSQL/pgvector must be available, normally from the root Docker Compose stack.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
export DATABASE_URL="postgresql+psycopg://naz_user:naz_password@localhost:5433/naz_order_papers"
export JWT_SECRET="replace-this-secret"
export FRONTEND_ORIGIN="http://localhost:3000"
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Endpoint Summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness. |
| `POST` | `/auth/login` | Authenticate and issue a JWT. |
| `GET` | `/auth/me` | Validate current JWT/database session. |
| `POST` | `/auth/logout` | Revoke current session. |
| `POST` | `/users/{id}/unlock` | Permission-protected account unlock. |
| `GET` | `/sessions` | List parliamentary sessions. |
| `POST` | `/submissions` | Create a question or motion. |
| `GET` | `/submissions/mine` | List current user's submissions. |
| `GET` | `/submissions/review-queue` | List Clerk review queue. |
| `PATCH` | `/submissions/{id}` | Edit an owned draft. |
| `POST` | `/submissions/{id}/submit` | Resubmit an owned draft. |
| `POST` | `/submissions/{id}/workflow-review` | Approve, reject, or request changes. |
| `POST` | `/submissions/{id}/schedule` | Schedule an approved item. |
| `GET` | `/records` | List/filter records. |
| `GET` | `/records/{id}` | Record detail. |
| `GET` | `/records/{id}/similar` | BM25/pgvector candidates. |
| `GET` | `/records/{id}/reviews` | Similarity decision history. |
| `POST` | `/records/{id}/reviews` | Record a similarity decision. |
| `POST` | `/search` | Ranked BM25 keyword search. |
| `GET` | `/order-papers/{date}` | Generate sitting Order Paper JSON. |
| `GET` | `/reports` | Permission-protected aggregate reports. |
| `GET` | `/audit` | Permission-protected audit trail. |

See [the full API specification](../docs/system-specification.md#14-api-contract).

## Authentication and Authorization

- bcrypt cost 12 password hashes.
- HS256 JWTs valid for eight hours.
- `user_sessions` JTI rows support logout revocation.
- Five failed passwords lock an account.
- Routes authorize atomic permissions inherited through data roles.
- Draft ownership and archive permissions also constrain row visibility.

## Database

SQLAlchemy 2 uses synchronous psycopg 3 sessions. PostgreSQL extensions:

- `pgcrypto` for UUID defaults;
- `vector` for optional 384-dimensional embeddings.

`app/db_compat.py` applies compatibility DDL and RBAC seeding at startup. For a
production release process, replace this with versioned migrations.

## Tests

The isolated test database is `naz_order_papers_test` on host port 5433.

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

Do not run backend pytest processes in parallel: the suite rebuilds one shared test
schema for isolation.

## CSV Import

```bash
PYTHONPATH=backend python backend/scripts/ingest_csv.py /path/to/records.csv
```

Required columns are `item_type`, `session_code`, `member`, `subject`, and
`full_text`; `ministry` and `status` are optional. Blank/unsupported legacy
statuses normalize to `Archived`.
