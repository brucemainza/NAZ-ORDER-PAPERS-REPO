from datetime import datetime, timedelta, timezone

from app.lib.auth import create_access_token, get_password_hash
from app.models import Permission, Role, User, UserSession


def create_user(db_session, employee_id="EMP-LOCK-001"):
    user = User(
        employee_id=employee_id,
        name="Lockout User",
        role="Viewer",
        status="Active",
        password_hash=get_password_hash("CorrectPassword!"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def failed_login(client, employee_id):
    return client.post(
        "/auth/login",
        json={
            "employee_id": employee_id,
            "password": "IncorrectPassword!",
        },
    )


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


def test_four_failures_do_not_lock_and_success_resets_counter(client, db_session):
    user = create_user(db_session)

    for _ in range(4):
        assert failed_login(client, user.employee_id).status_code == 401

    db_session.refresh(user)
    assert user.failed_login_attempts == 4
    assert user.locked_at is None

    response = client.post(
        "/auth/login",
        json={
            "employee_id": user.employee_id,
            "password": "CorrectPassword!",
        },
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.failed_login_attempts == 0


def test_fifth_failure_locks_account(client, db_session):
    user = create_user(db_session)

    for _ in range(5):
        assert failed_login(client, user.employee_id).status_code == 401

    db_session.refresh(user)
    assert user.failed_login_attempts == 5
    assert user.locked_at is not None


def test_locked_account_rejects_correct_password(client, db_session):
    user = create_user(db_session)
    for _ in range(5):
        failed_login(client, user.employee_id)

    response = client.post(
        "/auth/login",
        json={
            "employee_id": user.employee_id,
            "password": "CorrectPassword!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid employee ID or password."


def test_manage_users_permission_can_unlock_account(client, db_session):
    target = create_user(db_session)
    target.failed_login_attempts = 5
    target.locked_at = datetime.now(timezone.utc)

    permission = Permission(code="manage_users", description="Manage users")
    administrator_role = Role(
        name="Account Administrator",
        permissions=[permission],
    )
    administrator = create_user(db_session, employee_id="EMP-LOCK-ADMIN")
    administrator.roles.append(administrator_role)
    db_session.commit()
    headers = auth_headers(db_session, administrator)

    response = client.post(f"/users/{target.id}/unlock", headers=headers)

    assert response.status_code == 200
    db_session.refresh(target)
    assert target.failed_login_attempts == 0
    assert target.locked_at is None


def test_user_without_manage_users_permission_cannot_unlock_account(
    client,
    db_session,
):
    target = create_user(db_session)
    target.failed_login_attempts = 5
    target.locked_at = datetime.now(timezone.utc)

    viewer = create_user(db_session, employee_id="EMP-LOCK-VIEWER")
    viewer.roles.append(Role(name="Restricted Viewer", permissions=[]))
    db_session.commit()

    response = client.post(
        f"/users/{target.id}/unlock",
        headers=auth_headers(db_session, viewer),
    )

    assert response.status_code == 403
    db_session.refresh(target)
    assert target.failed_login_attempts == 5
    assert target.locked_at is not None
