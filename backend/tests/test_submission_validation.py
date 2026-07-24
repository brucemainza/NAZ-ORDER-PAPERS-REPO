from datetime import date, datetime, timedelta, timezone

import pytest

from app.lib.auth import create_access_token
from app.models import (
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)


def create_submission_context(db_session):
    session = ParliamentarySession(
        code="TEST-VALIDATION-SESSION",
        name="Validation Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    permissions = [
        Permission(code="submit_question", description="Submit questions"),
        Permission(code="submit_motion", description="Submit motions"),
    ]
    user = User(
        employee_id="EMP-VALIDATION-001",
        name="Validation Submitter",
        role="Viewer",
        status="Active",
        roles=[Role(name="Validation Submitter", permissions=permissions)],
    )
    db_session.add_all([session, user])
    db_session.commit()

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
    return session, {"Authorization": f"Bearer {token}"}


def valid_question(session_id):
    return {
        "item_type": "Question",
        "answer_type": "Written",
        "session_id": str(session_id),
        "member": "Hon. Validation Member",
        "ministry": "Ministry of Education",
        "subject": "Teacher accommodation in rural districts",
        "full_text": (
            "What steps will the Ministry take to improve teacher "
            "accommodation in rural districts during this session?"
        ),
    }


def valid_motion(session_id):
    return {
        "item_type": "Motion",
        "session_id": str(session_id),
        "member": "Hon. Validation Member",
        "subject": "Improving teacher accommodation",
        "full_text": (
            "That this House urges the Government to expand teacher "
            "accommodation programmes in rural districts."
        ),
    }


@pytest.mark.parametrize(
    ("item_type", "field_name", "error_hint"),
    [
        ("Question", "item_type", "item_type"),
        ("Question", "session_id", "session_id"),
        ("Question", "member", "member"),
        ("Question", "ministry", "ministry"),
        ("Question", "answer_type", "answer type"),
        ("Question", "subject", "subject"),
        ("Question", "full_text", "full_text"),
        ("Motion", "item_type", "item_type"),
        ("Motion", "session_id", "session_id"),
        ("Motion", "member", "member"),
        ("Motion", "subject", "subject"),
        ("Motion", "full_text", "full_text"),
    ],
)
def test_missing_required_field_returns_clear_validation_error(
    client,
    db_session,
    item_type,
    field_name,
    error_hint,
):
    session, headers = create_submission_context(db_session)
    payload = (
        valid_question(session.id)
        if item_type == "Question"
        else valid_motion(session.id)
    )
    payload.pop(field_name)

    response = client.post("/submissions", json=payload, headers=headers)

    assert response.status_code == 422
    assert error_hint in str(response.json()["detail"]).lower()


@pytest.mark.parametrize(
    ("field_name", "blank_value"),
    [
        ("member", "   "),
        ("ministry", "   "),
        ("subject", "     "),
        ("full_text", " " * 40),
    ],
)
def test_whitespace_only_required_field_is_rejected(
    client,
    db_session,
    field_name,
    blank_value,
):
    session, headers = create_submission_context(db_session)
    payload = valid_question(session.id)
    payload[field_name] = blank_value

    response = client.post("/submissions", json=payload, headers=headers)

    assert response.status_code == 422
    assert field_name in str(response.json()["detail"]).lower()


@pytest.mark.parametrize("item_type", ["Question", "Motion"])
def test_submission_with_all_required_fields_succeeds(
    client,
    db_session,
    item_type,
):
    session, headers = create_submission_context(db_session)
    payload = (
        valid_question(session.id)
        if item_type == "Question"
        else valid_motion(session.id)
    )

    response = client.post("/submissions", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["record"]["item_type"] == item_type
