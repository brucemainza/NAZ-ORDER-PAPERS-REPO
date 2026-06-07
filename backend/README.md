# NAZ Order Papers - Backend

FastAPI service handling authentication, parliamentary records, text search, and pgvector similarity queries.

## Local Development (No Docker)

Requires PostgreSQL running locally or via Docker Compose from project root.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

export DATABASE_URL="postgresql+psycopg://naz_user:naz_password@localhost:5433/naz_order_papers"
export JWT_SECRET="naz-order-papers-jwt-secret-change-in-production"
export FRONTEND_ORIGIN="http://localhost:3000"

uvicorn app.main:app --reload --port 8000

API docs auto-generate at http://localhost:8000/docs


## Endpoints
| Method | Path             | Description                                      |
| ------ | ---------------- | ------------------------------------------------ |
| GET    | `/health`        | Liveness check                                   |
| POST   | `/auth/login`    | Employee ID + password → JWT                     |
| GET    | `/auth/me`       | Validate Bearer token → user                     |
| POST   | `/auth/logout`   | Revoke session                                   |
| GET    | `/sessions`      | List parliamentary sessions                      |
| GET    | `/records`       | List records (filter by session\_id, item\_type) |
| GET    | `/records/{id}`  | Single record detail                             |
| GET    | `/records/{id}/similar` | Previously addressed record candidates       |
| POST   | `/records/{id}/reviews` | Record clerk review decisions                 |
| POST   | `/submissions`   | Submit a new question or motion                 |
| GET    | `/audit`         | Authorized audit trail access                    |
| GET    | `/reports`       | Operational reports and activity summaries       |
| POST   | `/search`        | BM25 text search                                 |
| POST   | `/search/vector` | pgvector cosine similarity                       |

## Auth
Passwords hashed with bcrypt (cost 12). JWTs signed with HS256, expire in 8 hours. Sessions tracked in user_sessions table for server-side revocation. Inactive accounts are rejected at login.

## Database Driver
Uses SQLAlchemy 2.x with psycopg3 (synchronous). The psycopg-binary package provides precompiled wheels to avoid build dependencies. Async migration to asyncpg is possible if needed later.

## Data Ingestion
**backend/scripts/ingest_csv.py** imports parliamentary records from CSV into the database. Expects columns: item_type, session_code, member, ministry, subject, full_text, status

python scripts/ingest_csv.py /path/to/records.csv