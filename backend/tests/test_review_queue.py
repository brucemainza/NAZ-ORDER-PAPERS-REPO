from datetime import date, datetime, timedelta, timezone

from app.lib.auth import create_access_token
from app.models import (
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)


def create_active_session(db_session):
    session = ParliamentarySession(
        code="TEST-REVIEW-SESSION",
        name="Review Queue Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db_session.add(session)
    db_session.commit()
    return session


def create_user(db_session, employee_id, *permission_codes):
    permissions = [
        Permission(code=code, description=code.replace("_", " ").title())
        for code in permission_codes
    ]
    user = User(
        employee_id=employee_id,
        name=employee_id.replace("-", " ").title(),
        role="Viewer",
        status="Active",
        roles=[Role(name=f"{employee_id} Role", permissions=permissions)],
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


def question_payload(session_id):
    return {
        "item_type": "Question",
        "answer_type": "Oral",
        "session_id": str(session_id),
        "member": "Hon. Review Member",
        "ministry": "Ministry of Local Government",
        "subject": "Water supply in district facilities",
        "full_text": (
            "What measures will the Ministry take to improve reliable water "
            "supply in district public facilities during this session?"
        ),
    }


def test_submission_enters_under_review_queue_for_reviewer(
    client,
    db_session,
):
    session = create_active_session(db_session)
    submitter = create_user(
        db_session,
        "EMP-REVIEW-SUBMITTER",
        "submit_question",
    )
    reviewer = create_user(
        db_session,
        "EMP-REVIEW-CLERK",
        "review_submission",
    )

    submission_response = client.post(
        "/submissions",
        json=question_payload(session.id),
        headers=auth_headers(db_session, submitter),
    )

    assert submission_response.status_code == 201
    submitted_record = submission_response.json()["record"]
    assert submitted_record["status"] == "Under Review"

    queue_response = client.get(
        "/submissions/review-queue",
        headers=auth_headers(db_session, reviewer),
    )

    assert queue_response.status_code == 200
    assert [record["id"] for record in queue_response.json()] == [
        submitted_record["id"]
    ]


def test_user_without_review_submission_permission_cannot_query_queue(
    client,
    db_session,
):
    user = create_user(db_session, "EMP-REVIEW-VIEWER")

    response = client.get(
        "/submissions/review-queue",
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 403
