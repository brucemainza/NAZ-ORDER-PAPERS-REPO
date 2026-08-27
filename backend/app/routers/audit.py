from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import AuditLog, User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    request: Request,
    user_filter: str | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    cursor: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("view_audit")),
) -> list[AuditLogOut]:
    query = select(AuditLog, User.name).outerjoin(User, AuditLog.user_id == User.id)

    if user_filter:
        query = query.where(User.name.ilike(f"%{user_filter}%"))
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if entity_id:
        query = query.where(
            or_(
                AuditLog.entity_id == entity_id,
                AuditLog.details.ilike(f"%{entity_id}%"),
            )
        )
    if cursor is not None:
        cursor_entry = db.get(AuditLog, cursor)
        if cursor_entry is None:
            raise HTTPException(status_code=404, detail="Audit cursor not found")
        query = query.where(
            or_(
                AuditLog.created_at < cursor_entry.created_at,
                and_(
                    AuditLog.created_at == cursor_entry.created_at,
                    AuditLog.id < cursor_entry.id,
                ),
            )
        )

    rows = db.execute(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
    ).all()
    add_audit_log(
        db,
        user_id=user.id,
        action="audit_read",
        entity_type="audit_log",
        details="Viewed audit trail",
        ip_address=request_ip(request),
    )
    db.commit()

    return [
        AuditLogOut(
            id=entry.id,
            user_id=entry.user_id,
            user_name=user_name,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            details=entry.details,
            ip_address=entry.ip_address,
            created_at=entry.created_at,
        )
        for entry, user_name in rows
    ]
