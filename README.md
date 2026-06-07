# Order Papers System

Internal parliamentary document management and similarity retrieval platform for the National Assembly of Zambia.

## What's Working

- Docker-based local development (PostgreSQL + pgvector, FastAPI backend, Next.js frontend)
- JWT authentication with httpOnly cookies and server-side session revocation
- Role-based access control (Admin, Senior Clerk, Clerk)
- Parliamentary session management
- Record search with BM25 text ranking
- pgvector cosine similarity endpoint for semantic duplicate detection

## Tech Stack

- Next.js 14 (App Router)
- Tailwind CSS
- FastAPI + SQLAlchemy + psycopg3
- PostgreSQL 16 with pgvector extension
- Docker Compose for local orchestration

## Quick Start

### Prerequisites

- Docker with Compose
- Node.js 20+ (for local frontend dev without Docker)
- Python 3.11+ (for local backend dev without Docker)

### Full Stack (Docker)

```bash
docker compose up --build
```

## Services:

    Frontend: http://localhost:3000
    Backend API: http://localhost:8080
    API docs: http://localhost:8080/docs
    Portainer: http://localhost:9000
    Database: localhost:5433 (PostgreSQL with pgvector)

## Seeded Login Credentials
| Employee ID | Name           | Role         | Status   |
| ----------- | -------------- | ------------ | -------- |
| EMP-001     | Lilian Mwape   | Admin        | Active   |
| EMP-002     | Patrick Zulu   | Admin        | Active   |
| EMP-003     | Naomi Chisanga | Senior Clerk | Active   |
| EMP-004     | Brian Musonda  | Clerk        | Active   |
| EMP-005     | Mercy Siame    | Clerk        | Inactive |

Password for all active accounts: **Password123!**

## Environment Variables
Copy frontend/.env.local.example to frontend/.env.local and adjust if needed:

    NEXT_PUBLIC_API_URL — Next.js internal API base URL
    NEXT_PUBLIC_BACKEND_URL — FastAPI backend external URL
    BACKEND_INTERNAL_URL — FastAPI backend Docker network URL
    JWT_SECRET — Shared secret for JWT signing (must match backend)
    DATABASE_URL — PostgreSQL connection string

Backend reads from environment or .env:

    DATABASE_URL - PostgreSQL connection
    FRONTEND_ORIGIN - CORS allowed origin
    JWT_SECRET - Must match frontend

## Architecture Notes
Authentication Flow

    User submits credentials to Next.js /api/auth/login
    Next.js proxies to FastAPI /auth/login
    FastAPI verifies bcrypt hash against PostgreSQL users table
    FastAPI issues JWT with jti claim and stores session in user_sessions
    Next.js sets naz_token httpOnly cookie
    Middleware verifies JWT signature locally (fast, no network)
    /api/auth/me refreshes user data from FastAPI on page load
    Logout revokes session in database and clears cookie

## Why Proxy Routes?
The frontend uses Next.js API routes as proxies to the FastAPI backend. This keeps auth cookies httpOnly (never exposed to browser JS) while allowing the frontend to make same-origin requests. CORS is handled at the proxy layer, not the browser.

## Database
PostgreSQL 16 with pgvector extension. Key tables:

    users - staff accounts with bcrypt password hashes
    user_sessions - JWT session tracking for revocation
    parliamentary_sessions - assembly sessions (First, Second, etc.)
    parliamentary_records - questions and motions with embedding vector(384)
    search_logs - query history for audit
    review_decisions - manual similarity review outcomes
    audit_logs - system activity trail

## Development
**Backend Only**
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   export DATABASE_URL="postgresql+psycopg://naz_user:naz_password@localhost:5433/naz_order_papers"
   export JWT_SECRET="your-secret-here"
   uvicorn app.main:app --reload --port 8000

**Frontend Only**
   cd frontend
   npm install
   cp .env.local.example .env.local
   npm run dev

## Current Limitations
   - No password reset or change-password flow
   - Admin user management page exists but is not wired to backend CRUD
   - pgvector search requires pre-computed embeddings (not yet generated for seed data)
   - No CSV upload UI (script exists at backend/scripts/ingest_csv.py)

## Implementation Notes
- New submissions are persisted as `parliamentary_records` and connected to parliamentary sessions.
- Submitted items are evaluated against historical records using BM25 and pgvector similarity.
- Review decisions are stored in `review_decisions` and update record status to support duplicate handling.
- Audit events are persisted for login, logout, submission, search, record retrieval, similarity lookup, duplicate review, and report access.
- Reports are returned from `/reports` and include session summaries, similarity match rate, member activity, and department activity.

## Contributing
This is a team project with three active contributors. Coordinate branch naming:
   feature-maliseni1
   feature-daliD
   feat/mainza