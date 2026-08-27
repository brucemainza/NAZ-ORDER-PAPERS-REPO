# NAZ Order Papers System

Internal parliamentary submission, review, scheduling, archive, and similarity
retrieval platform for the National Assembly of Zambia.

## Documentation

- [Full system specification](docs/system-specification.md)
- [Graphical system architecture](docs/system-architecture.md)
- [File-by-file application guide](docs/file-guide.md)
- [TDD implementation and verification report](docs/implementation-report.md)
- [Pre-implementation baseline](docs/implementation-baseline.md)
- [Production AI implementation (offline HTML)](docs/ai-explanation.html)

## Implemented Capabilities

- Employee-ID/password login with HTTP-only JWT cookie and revocable sessions.
- Account lock after five failed attempts and administrator unlock.
- Configurable Permission -> Role -> User RBAC.
- Question submission for oral or written answer.
- Notice-of-motion submission.
- Required-field validation with readable browser errors.
- Submission ownership, draft recovery, resubmission, and status tracking.
- Clerk review queue with approve, reject, and request-changes actions.
- Separate similarity/duplicate review decisions.
- Exact seven-state submission lifecycle.
- Approved-item scheduling for sitting dates.
- Structured Order Paper generation from scheduled items.
- Automatic startup archival after session end.
- Permission-controlled archive list/detail/search.
- PostgreSQL weighted full-text and versioned chunk-vector hybrid search with
  relevance context, structured filters, and lexical-only degradation.
- Durable PostgreSQL worker processing for indexing and explanations.
- Grounded local-Ollama explanations with evidence validation and mandatory human
  review.
- Reports, audit trail, and audit CSV export.
- Plain CSS UI with desktop/mobile Playwright visual baselines.

## Technology

- Next.js 14 App Router, React 18, plain CSS.
- FastAPI, Pydantic, SQLAlchemy 2, psycopg 3.
- PostgreSQL 16 with pgvector.
- Local Ollama embeddings and structured explanation generation.
- bcrypt password hashing and HS256 JWTs.
- Docker Compose.
- pytest, Node test runner, and Playwright/Chrome.

## Quick Start

Prerequisite: Docker with Compose.

```bash
docker compose up --build
```

Services:

| Service | URL/port |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8080 |
| Swagger UI | http://localhost:8080/docs |
| ReDoc | http://localhost:8080/redoc |
| PostgreSQL | localhost:5433 |

### Local Ollama connectivity

The application uses the standard Ollama API port `11434`. The backend and
worker connect to `http://host.docker.internal:11434`. On Linux, Ollama must
listen on an address reachable from Docker; bind it to the Docker bridge
(`172.17.0.1:11434` on the default engine) or set
`OLLAMA_HOST=0.0.0.0:11434` and restrict port `11434` to Docker bridge traffic
with the host firewall. Do not expose the Ollama API to untrusted networks.

## Seeded Login

| Employee ID | Name | Legacy display role | Status |
| --- | --- | --- | --- |
| `EMP-001` | Lilian Mwape | Admin | Active |
| `EMP-002` | Patrick Zulu | Admin | Active |
| `EMP-003` | Naomi Chisanga | Senior Clerk | Active |
| `EMP-004` | Brian Musonda | Clerk | Active |
| `EMP-005` | Mercy Siame | Clerk | Inactive |

Password for active seeded accounts: `Password123!`

The compatibility display roles are mapped to configurable Administrator and Clerk
role records at startup.

## Architecture Summary

```mermaid
flowchart LR
    B[Browser]
    N[Next.js UI + BFF]
    A[FastAPI]
    P[(PostgreSQL + pgvector)]

    B -->|Same-origin /api requests| N
    N -->|Bearer JWT + JSON| A
    A -->|SQLAlchemy / vector SQL| P
```

Next.js route handlers keep the JWT in an HTTP-only cookie and forward it to
FastAPI. FastAPI validates the JWT, database session, account, permissions, and row
visibility before business operations.

## Environment

Docker Compose supplies normal local defaults. Important variables:

| Variable | Used by | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | FastAPI/scripts | PostgreSQL connection. |
| `FRONTEND_ORIGIN` | FastAPI | Allowed CORS origin. |
| `JWT_SECRET` | FastAPI and Next.js | Shared JWT signing/verification secret. |
| `BACKEND_INTERNAL_URL` | Next.js | Docker-network FastAPI URL. |
| `NEXT_PUBLIC_API_URL` | Browser Axios client | Same-origin BFF base when explicitly set. |
| `NEXT_PUBLIC_BACKEND_URL` | Legacy direct client | External backend URL for retained helper. |

Never use the checked-in development JWT fallback in production.

## Local Backend

With PostgreSQL available on host port 5433:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
export DATABASE_URL="postgresql+psycopg://naz_user:naz_password@localhost:5433/naz_order_papers"
export JWT_SECRET="replace-this-secret"
export FRONTEND_ORIGIN="http://localhost:3000"
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

## Local Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

When the frontend runs on the host instead of Docker, set
`BACKEND_INTERNAL_URL=http://localhost:8080` in `frontend/.env.local`.

## EC2 Deployment

Use [the EC2 deployment runbook](docs/operations/ec2-deployment.md). It covers
the production Compose file, Ollama provisioning, HTTPS exposure, migrations,
release checks, and encrypted backups.

## Verification

Backend:

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

Frontend source guards and production build:

```bash
cd frontend
npm run test:source
npm run build
```

Browser E2E and pixel snapshots:

```bash
cd frontend
npm run test:e2e
```

Update visual snapshots only after inspecting the browser capture:

```bash
cd frontend
npm run test:e2e:update
```

## Data Import

CSV columns:

- `item_type`
- `session_code`
- `member`
- `ministry`
- `subject`
- `full_text`
- optional `status`

Run:

```bash
PYTHONPATH=backend python backend/scripts/ingest_csv.py /path/to/records.csv
```

Blank/legacy unsupported statuses are normalized to `Archived`.

## Current Product Limits

- Generated Order Papers are structured JSON, not official PDF/print documents.
- Ended-session archival runs at API startup rather than in a continuous worker.
- Users and Sessions management pages currently change local demo state; persistent
  CRUD APIs are not implemented.
- Authentication hardening remains explicitly out of scope and its frozen PyJWT
  dependency is a documented residual go-live risk.
- Rate limiting, MFA, and password-reset facilities are not included.
