from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.reports.session_report import (
    DatabaseSessionReportReader,
    SessionReportReader,
)


def get_session_report_reader(
    db: Session = Depends(get_db),
) -> SessionReportReader:
    return DatabaseSessionReportReader(db)
