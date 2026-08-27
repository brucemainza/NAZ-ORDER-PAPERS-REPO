from datetime import date, datetime, timedelta, timezone

from app.lib.auth import create_access_token
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)


def create_active_session(db_session):
    session = ParliamentarySession(
        code="TEST-MOTION-SESSION",
        name="Motion Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db_session.add(session)
    db_session.commit()
    return session


def create_user_with_permissions(db_session, *permission_codes):
    permissions = [
        Permission(code=code, description=code.replace("_", " ").title())
        for code in permission_codes
    ]
    role = Role(name="Motion Submission Role", permissions=permissions)
    user = User(
        employee_id="EMP-MOTION-001",
        name="Motion Submitter",
        role="Viewer",
        status="Active",
        roles=[role],
    )
    db_session.add(user)
    db_session.commit()
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


def motion_payload(session_id):
    return {
        "item_type": "Motion",
        "session_id": str(session_id),
        "member": "Hon. Motion Member",
        "subject": "Expansion of rural road maintenance",
        "full_text": (
            "That this House urges the Government to expand routine road "
            "maintenance programmes in rural districts during the next "
            "financial year."
        ),
    }


def test_user_with_submit_motion_permission_can_submit_notice_of_motion(
    client,
    db_session,
):
    session = create_active_session(db_session)
    user = create_user_with_permissions(db_session, "submit_motion")

    response = client.post(
        "/submissions",
        json=motion_payload(session.id),
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 201
    assert response.json()["record"]["item_type"] == "Motion"
    assert response.json()["record"]["answer_type"] is None
    assert db_session.query(ParliamentaryRecord).count() == 1


def test_user_without_submit_motion_permission_cannot_submit_notice_of_motion(
    client,
    db_session,
):
    session = create_active_session(db_session)
    user = create_user_with_permissions(db_session, "submit_question")

    response = client.post(
        "/submissions",
        json=motion_payload(session.id),
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 403
    assert db_session.query(ParliamentaryRecord).count() == 0
