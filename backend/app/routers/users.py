from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/{user_id}/unlock")
def unlock_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    administrator: User = Depends(require_permission("manage_users")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.failed_login_attempts = 0
    user.locked_at = None
    add_audit_log(
        db,
        user_id=administrator.id,
        action="account_unlock",
        entity_type="user",
        entity_id=str(user.id),
        details=user.employee_id,
        ip_address=request_ip(request),
    )
    db.commit()
    return {"success": True}
