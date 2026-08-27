from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import ParliamentaryRecord, ParliamentarySession, ReviewDecision, User
from app.schemas.report import ActivityReport, MatchRateReport, ReportsResponse, SessionSubmissionReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportsResponse)
def reports(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("view_reports")),
) -> ReportsResponse:
    add_audit_log(
        db,
        user_id=user.id,
        action="report_access",
        entity_type="reports",
        details="Viewed reports dashboard",
        ip_address=request_ip(request),
    )

    duplicate_record_ids = select(ReviewDecision.record_id).where(
        ReviewDecision.is_duplicate.is_(True)
    )
    is_duplicate_record = ParliamentaryRecord.id.in_(duplicate_record_ids)

    session_rows = db.execute(
        select(
            ParliamentarySession.id,
            ParliamentarySession.code,
            ParliamentarySession.name,
            func.count(ParliamentaryRecord.id),
            func.sum(case((ParliamentaryRecord.item_type == "Question", 1), else_=0)),
            func.sum(case((ParliamentaryRecord.item_type == "Motion", 1), else_=0)),
            func.sum(case((ParliamentaryRecord.status == "Under Review", 1), else_=0)),
            func.sum(case((is_duplicate_record, 1), else_=0)),
        )
        .join(ParliamentaryRecord, ParliamentaryRecord.session_id == ParliamentarySession.id, isouter=True)
        .group_by(ParliamentarySession.id)
        .order_by(ParliamentarySession.start_date.desc())
    ).all()

    match_rows = db.execute(
        select(
            func.date(ReviewDecision.created_at),
            func.count(ReviewDecision.id),
            func.sum(case((ReviewDecision.is_duplicate.is_(True), 1), else_=0)),
        )
        .group_by(func.date(ReviewDecision.created_at))
        .order_by(func.date(ReviewDecision.created_at))
    ).all()

    member_rows = db.execute(
        select(
            ParliamentaryRecord.member,
            func.min(ParliamentaryRecord.ministry),
            func.count(ParliamentaryRecord.id),
            func.sum(case((ParliamentaryRecord.status == "Under Review", 1), else_=0)),
            func.sum(case((is_duplicate_record, 1), else_=0)),
        )
        .group_by(ParliamentaryRecord.member)
        .order_by(func.count(ParliamentaryRecord.id).desc())
        .limit(10)
    ).all()

    department_rows = db.execute(
        select(
            func.coalesce(ParliamentaryRecord.ministry, "Motions / No department"),
            func.count(ParliamentaryRecord.id),
            func.sum(case((ParliamentaryRecord.status == "Under Review", 1), else_=0)),
            func.sum(case((is_duplicate_record, 1), else_=0)),
        )
        .group_by(ParliamentaryRecord.ministry)
        .order_by(func.count(ParliamentaryRecord.id).desc())
        .limit(10)
    ).all()

    db.commit()

    return ReportsResponse(
        submissions_by_session=[
            SessionSubmissionReport(
                session_id=row[0],
                session_code=row[1],
                session_name=row[2],
                total=row[3] or 0,
                questions=row[4] or 0,
                motions=row[5] or 0,
                pending_review=row[6] or 0,
                duplicates=row[7] or 0,
            )
            for row in session_rows
        ],
        similarity_match_rate=[
            MatchRateReport(
                period=row[0],
                total_reviews=row[1] or 0,
                duplicate_or_similar=row[2] or 0,
                match_rate=round(((row[2] or 0) / (row[1] or 1)) * 100, 2),
            )
            for row in match_rows
        ],
        member_activity=[
            ActivityReport(
                name=row[0],
                department=row[1],
                submissions=row[2] or 0,
                pending_review=row[3] or 0,
                duplicates=row[4] or 0,
            )
            for row in member_rows
        ],
        department_activity=[
            ActivityReport(
                name=row[0],
                department=row[0],
                submissions=row[1] or 0,
                pending_review=row[2] or 0,
                duplicates=row[3] or 0,
            )
            for row in department_rows
        ],
    )
