# Backend

FastAPI backend for the NAZ Order Papers system.

## Setup

1. Start the Docker database from the project root:

   ```powershell
   cd C:\Users\zdali\NAZ-ORDER-PAPERS-REPO\order-papers
   docker compose up -d
   ```

2. Create and activate a Python virtual environment:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Run the API:

   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

6. Open the API docs:

   ```text
   http://localhost:8000/docs
   ```

## Current Endpoints

- `GET /health`
- `GET /sessions`
- `GET /records`
- `GET /records/{record_id}`
- `POST /search`

## Note On The Database Driver

This first backend slice uses SQLAlchemy with the `psycopg` binary driver so it installs cleanly on Windows. If the team standardises on Python 3.12 or 3.13 later, the backend can be switched to SQLAlchemy async with `asyncpg`.
