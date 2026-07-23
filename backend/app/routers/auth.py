from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip
from app.lib.auth import create_access_token, verify_access_token, verify_password
from app.models.models import User, UserSession
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        employeeId=user.employee_id,
        name=user.name,
        role=user.primary_role_name,
        roles=user.role_names,
        permissions=user.permission_codes,
        status=user.status,
        lastLogin=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    employee_id = request.employee_id.strip().upper()

    result = db.execute(select(User).where(User.employee_id == employee_id))
    user = result.scalars().first()

    if not user or user.status != "Active":
        raise HTTPException(status_code=401, detail="Invalid employee ID or password.")

    if not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid employee ID or password.")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid employee ID or password.")

    user.last_login_at = datetime.now(timezone.utc)

    token, jti = create_access_token({
        "sub": str(user.id),
        "employeeId": user.employee_id,
        "name": user.name,
        "role": user.primary_role_name,
        "roles": user.role_names,
        "permissions": user.permission_codes,
        "status": user.status,
    })

    ip_address = request_ip(req)
    user_agent = req.headers.get("user-agent")

    session = UserSession(
        user_id=user.id,
        jti=jti,
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    add_audit_log(
        db,
        user_id=user.id,
        action="login",
        entity_type="auth",
        entity_id=str(session.id),
        details=user.employee_id,
        ip_address=ip_address,
    )
    db.commit()

    return LoginResponse(
        token=token,
        user=user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user_id = UUID(payload.get("sub"))
    jti = payload.get("jti")

    session_result = db.execute(
        select(UserSession).where(
            UserSession.jti == jti,
            UserSession.revoked_at.is_(None),
        )
    )
    session = session_result.scalars().first()

    if not session:
        raise HTTPException(status_code=401, detail="Session revoked or expired")

    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "Active":
        raise HTTPException(status_code=401, detail="Account inactive")

    return user_out(user)


@router.post("/logout")
def logout(req: Request, credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    if credentials:
        payload = verify_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            jti = payload.get("jti")
            if jti:
                result = db.execute(select(UserSession).where(UserSession.jti == jti))
                session = result.scalars().first()
                if session:
                    session.revoked_at = datetime.now(timezone.utc)
                    add_audit_log(
                        db,
                        user_id=UUID(user_id) if user_id else None,
                        action="logout",
                        entity_type="auth",
                        entity_id=str(session.id),
                        details=jti,
                        ip_address=request_ip(req),
                    )
                    db.commit()
    return {"success": True}
