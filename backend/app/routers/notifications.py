from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AuditLog, User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[AuditLogOut])
def list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditLogOut]:
    query = select(AuditLog, User.name).outerjoin(User, AuditLog.user_id == User.id)

    if not user.has_permission("view_audit"):
        query = query.where(
            or_(AuditLog.user_id == user.id, AuditLog.user_id.is_(None))
        )

    rows = db.execute(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
    ).all()

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
