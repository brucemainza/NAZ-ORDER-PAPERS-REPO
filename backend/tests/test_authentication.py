from app.lib.auth import get_password_hash
from app.models import User


def create_login_user(db_session):
    user = User(
        employee_id="EMP-AUTH-001",
        name="Authentication User",
        role="Viewer",
        status="Active",
        password_hash=get_password_hash("CorrectPassword!"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_valid_credentials_succeed(client, db_session):
    user = create_login_user(db_session)

    response = client.post(
        "/auth/login",
        json={
            "employee_id": user.employee_id.lower(),
            "password": "CorrectPassword!",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token"]
    assert payload["user"]["employeeId"] == user.employee_id


def test_invalid_username_returns_generic_credentials_error(client, db_session):
    create_login_user(db_session)

    response = client.post(
        "/auth/login",
        json={
            "employee_id": "EMP-AUTH-UNKNOWN",
            "password": "CorrectPassword!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid employee ID or password."


def test_invalid_password_returns_same_generic_credentials_error(client, db_session):
    user = create_login_user(db_session)

    response = client.post(
        "/auth/login",
        json={
            "employee_id": user.employee_id,
            "password": "IncorrectPassword!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid employee ID or password."
