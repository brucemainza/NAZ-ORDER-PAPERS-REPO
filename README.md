# Order Papers System

Order Papers System is an internal parliamentary document management and similarity retrieval platform for the National Assembly of Zambia.

## Features

- Secure JWT-based authentication using httpOnly cookies
- Submission workflow for parliamentary questions and motions
- Historical search and similarity review for duplicate detection
- Session, user, audit, and reporting interfaces
- Mock-backed demo mode so the frontend runs without a backend

## Tech Stack

- Next.js 14 App Router 
- Tailwind CSS
- Zustand for auth state
- Axios for API communication
- React Hook Form with Zod validation
- Lucide React icons

## Project Structure

```text
order-papers/
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ...
├── backend/
│   └── .gitkeep
├── .gitignore
└── README.md
```

## Getting Started

1. Change into the frontend directory:

   ```bash
   cd frontend
   ```

2. Copy the example environment file:

   ```bash
   cp .env.local.example .env.local
   ```

3. Install dependencies:

   ```bash
   npm install
   ```

4. Start the development server:

   ```bash
   npm run dev
   ```

5. Open `http://localhost:3000`.

## Environment Variables

Create `frontend/.env.local` from `frontend/.env.local.example`.

- `NEXT_PUBLIC_API_URL`
  Use the base URL for the upstream backend API when it is available. For the demo scaffold, leave it as `http://localhost:3000`.
- `JWT_SECRET`
  Secret used to sign and verify the demo JWT stored in the `naz_token` cookie.

## Demo Login

Use any of the seeded employee IDs below with the shared demo password `Password123!`.

- `EMP-001`
- `EMP-002`
- `EMP-003`
- `EMP-004`
- `EMP-005`

## Notes

- The frontend currently uses mock data for sessions, submissions, similarity results, users, and audit logs.
- The backend folder is intentionally left empty for the next implementation phase.
- API route handlers under `frontend/src/app/api/auth/*` simulate auth until the real backend is connected.

## Database Setup Update 
The project database foundation has been added using Docker, PostgreSQL, and pgvector. A docker-compose.yml file was created to run a local PostgreSQL database with pgvector support through the pgvector/pgvector:pg16 image. This allows the team to run the same database environment locally without manually installing PostgreSQL.

The database container is named naz_order_papers_db and exposes PostgreSQL on port 5432. The configured database is naz_order_papers, with user naz_user.

Two SQL files were added under backend/db/ : schema.sql
seed.sql

schema.sql creates the initial database structure, including tables for users, parliamentary sessions, parliamentary records, search logs, review decisions, and audit logs. It also enables the required PostgreSQL extensions: vector for pgvector similarity search and pgcrypto for UUID generation. The parliamentary_records table includes an embedding vector(384) column, matching the planned all-MiniLM-L6-v2 embedding model.

seed.sql inserts initial sample data into the database, including five users, five parliamentary sessions, and five parliamentary records. This gives the project a working local dataset for testing future retrieval, search, and backend integration features.

The database was started using Docker Compose and verified through PostgreSQL queries to confirm that the tables and seed data were created successfully.
