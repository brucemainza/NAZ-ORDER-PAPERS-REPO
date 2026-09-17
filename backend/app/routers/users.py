import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.lib.auth import get_password_hash
from app.models import Role, User
from app.schemas.user import (
    PasswordResetResponse,
    UserCreate,
    UserCreateResponse,
    UserRoleUpdate,
    UserSummaryOut,
)
from app.services.transactions import (
    DatabaseConflict,
    commit_transaction,
    flush_transaction,
)

router = APIRouter(prefix="/users", tags=["users"])


def _generate_temporary_password() -> str:
    return secrets.token_urlsafe(12)


def _get_role_or_404(db: Session, role_name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def _serialize_user(user: User) -> UserSummaryOut:
    primary_role = user.roles[0].name if user.roles else user.role
    return UserSummaryOut(
        id=user.id,
        employee_id=user.employee_id,
        name=user.name,
        role=primary_role,
        status=user.status,
        last_login_at=user.last_login_at,
    )


@router.get("", response_model=list[UserSummaryOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("manage_users")),
) -> list[UserSummaryOut]:
    result = db.execute(select(User).order_by(User.name))
    return [_serialize_user(user) for user in result.scalars().all()]


@router.post("", response_model=UserCreateResponse, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    administrator: User = Depends(require_permission("manage_users")),
) -> UserCreateResponse:
    role = _get_role_or_404(db, payload.role_name)

    temporary_password = _generate_temporary_password()
    new_user = User(
        employee_id=payload.employee_id,
        name=payload.name,
        role=role.name,
        status=payload.status,
        password_hash=get_password_hash(temporary_password),
        roles=[role],
    )
    db.add(new_user)
    try:
        flush_transaction(
            db,
            conflict_message="A user with that Employee ID already exists",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    add_audit_log(
        db,
        user_id=administrator.id,
        action="user_create",
        entity_type="user",
        entity_id=str(new_user.id),
        details=new_user.employee_id,
        ip_address=request_ip(request),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The user conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    db.refresh(new_user)
    return UserCreateResponse(
        user=_serialize_user(new_user),
        temporary_password=temporary_password,
    )


@router.patch("/{user_id}/role", response_model=UserSummaryOut)
def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    administrator: User = Depends(require_permission("manage_users")),
) -> UserSummaryOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    role = _get_role_or_404(db, payload.role_name)

    target.roles = [role]
    target.role = role.name
    add_audit_log(
        db,
        user_id=administrator.id,
        action="user_role_update",
        entity_type="user",
        entity_id=str(target.id),
        details=role.name,
        ip_address=request_ip(request),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The user conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    db.refresh(target)
    return _serialize_user(target)


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_user_password(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    administrator: User = Depends(require_permission("manage_users")),
) -> PasswordResetResponse:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    temporary_password = _generate_temporary_password()
    target.password_hash = get_password_hash(temporary_password)
    target.failed_login_attempts = 0
    target.locked_at = None
    add_audit_log(
        db,
        user_id=administrator.id,
        action="user_password_reset",
        entity_type="user",
        entity_id=str(target.id),
        details=target.employee_id,
        ip_address=request_ip(request),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The user conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return PasswordResetResponse(temporary_password=temporary_password)


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
