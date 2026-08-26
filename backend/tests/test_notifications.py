from datetime import datetime, timedelta, timezone

from app.lib.auth import create_access_token
from app.models import AuditLog, Permission, Role, User, UserSession


def make_user(db_session, employee_id, permissions=()):
    role_permissions = [
        Permission(code=code, description=code.replace("_", " "))
        for code in permissions
    ]
    role = Role(name=f"Role {employee_id}", permissions=role_permissions)
    user = User(
        employee_id=employee_id,
        name=f"User {employee_id}",
        role="Legacy",
        roles=[role],
        status="Active",
        password_hash=None,
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


def test_notifications_show_personal_and_system_activity_to_regular_users(client, db_session):
    user = make_user(db_session, "EMP-NOTIFY-001")
    other_user = make_user(db_session, "EMP-NOTIFY-002")
    db_session.add_all(
        [
            AuditLog(user_id=user.id, action="submission_created", details="Own submission"),
            AuditLog(user_id=other_user.id, action="submission_created", details="Other submission"),
            AuditLog(user_id=None, action="session_changed", details="Session updated"),
        ]
    )
    headers = auth_headers(db_session, user)

    response = client.get("/notifications", headers=headers)

    assert response.status_code == 200
    details = {entry["details"] for entry in response.json()}
    assert details == {"Own submission", "Session updated"}


def test_notifications_show_full_activity_to_auditors(client, db_session):
    auditor = make_user(db_session, "EMP-NOTIFY-003", permissions=("view_audit",))
    other_user = make_user(db_session, "EMP-NOTIFY-004")
    db_session.add(
        AuditLog(user_id=other_user.id, action="workflow_review", details="Reviewed submission")
    )
    headers = auth_headers(db_session, auditor)

    response = client.get("/notifications", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["details"] == "Reviewed submission"
