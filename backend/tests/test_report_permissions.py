from datetime import datetime, timedelta, timezone

from app.lib.auth import create_access_token
from app.models import Permission, Role, User, UserSession


def create_user(db_session, employee_id, permissions=()):
    role_permissions = [
        Permission(code=code, description=f"Permission {code}")
        for code in permissions
    ]
    role = Role(
        name=f"Report Role {employee_id}",
        permissions=role_permissions,
    )
    user = User(
        employee_id=employee_id,
        name=f"Report User {employee_id}",
        role="Legacy",
        roles=[role],
        status="Active",
    )
    db_session.add(user)
    db_session.flush()
    return user


def auth_headers(db_session, user):
    token, jti = create_access_token({"sub": str(user.id)})
    now = datetime.now(timezone.utc)
    db_session.add(
        UserSession(
            user_id=user.id,
            jti=jti,
            issued_at=now,
            expires_at=now + timedelta(hours=8),
        )
    )
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


def test_reports_endpoint_uses_view_reports_permission(client, db_session):
    allowed = create_user(
        db_session,
        "EMP-REPORT-ALLOWED",
        permissions=("view_reports",),
    )
    denied = create_user(db_session, "EMP-REPORT-DENIED")
    allowed_headers = auth_headers(db_session, allowed)
    denied_headers = auth_headers(db_session, denied)

    denied_response = client.get("/reports", headers=denied_headers)
    allowed_response = client.get("/reports", headers=allowed_headers)

    assert denied_response.status_code == 403
    assert allowed_response.status_code == 200
