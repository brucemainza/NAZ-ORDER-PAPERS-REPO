from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import User
from app.reports.dependencies import get_session_report_reader
from app.reports.session_report import SessionReportReader
from app.schemas.session_report import SessionReportOut

router = APIRouter(
    prefix="/reports/sessions",
    tags=["reports"],
)


@router.get("/{session_id}", response_model=SessionReportOut)
def session_report(
    session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("view_reports")),
    reader: SessionReportReader = Depends(get_session_report_reader),
) -> SessionReportOut:
    report = reader.read(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Session not found")

    add_audit_log(
        db,
        user_id=user.id,
        action="session_report_access",
        entity_type="parliamentary_session",
        entity_id=str(session_id),
        details="Viewed JSON session report",
        ip_address=request_ip(request),
    )
    db.commit()
    return SessionReportOut.model_validate(report)
