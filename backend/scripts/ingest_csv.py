import csv
import os
import sys
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base
from app.models import ParliamentaryRecord, ParliamentarySession
from app.services.submission_status import SubmissionStatus


def normalize_status(status: str | None) -> str:
    try:
        return SubmissionStatus(status or SubmissionStatus.ARCHIVED).value
    except ValueError:
        return SubmissionStatus.ARCHIVED.value


def ingest_csv(csv_path: str, database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        # Get session mapping
        sessions = {
            s.code: s.id for s in session.query(ParliamentarySession).all()
        }

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = ParliamentaryRecord(
                    id=uuid4(),
                    item_type=row["item_type"],
                    session_id=sessions.get(row["session_code"]),
                    member=row["member"],
                    ministry=row.get("ministry") or None,
                    subject=row["subject"],
                    full_text=row["full_text"],
                    status=normalize_status(row.get("status")),
                )
                session.add(record)

        session.commit()
        print("Ingestion complete.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_csv.py <path_to_csv>")
        sys.exit(1)

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://naz_user:naz_password@localhost:5433/naz_order_papers",
    )
    ingest_csv(sys.argv[1], db_url)
