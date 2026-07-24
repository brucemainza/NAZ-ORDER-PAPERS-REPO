import importlib
import importlib.util
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.lib.auth import create_access_token
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)


def _load_response_service_module():
    qualified_name = "app.responses.service"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-040 response-recording service has not been implemented"
    )
    return importlib.import_module(qualified_name)


def _session():
    return ParliamentarySession(
        code=f"RESPONSE-{uuid4()}",
        name="Response Recording Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )


def _user(db_session, *, prefix, permission_codes=()):
    permissions = [
        Permission(code=code, description=code.replace("_", " ").title())
        for code in permission_codes
    ]
    user = User(
        employee_id=f"{prefix}-{uuid4()}",
        name=f"{prefix} User",
        role="Clerk" if "record_response" in permission_codes else "Member",
        status="Active",
        roles=[
            Role(
                name=f"{prefix} Role {uuid4()}",
                permissions=permissions,
            )
        ],
    )
    db_session.add(user)
    db_session.commit()
    return user


def _headers(db_session, user):
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


def _question(*, status="Scheduled"):
    return ParliamentaryRecord(
        item_type="Question",
        session=_session(),
        member="Hon. Response Member",
        ministry="Water Development",
        answer_type="Oral",
        subject="Rural borehole implementation response",
        full_text=(
            "What progress has been made on rural borehole implementation "
            "during the current parliamentary session?"
        ),
        status=status,
        sitting_date=date(2026, 9, 14),
    )


def _payload():
    return {
        "response_text": (
            "The Ministry completed 120 boreholes and has scheduled another "
            "80 for completion before the end of the financial year."
        ),
        "response_date": "2026-09-14",
    }


def test_clerk_can_record_response_text_and_date(client, db_session):
    _load_response_service_module()
    models = importlib.import_module("app.models")
    clerk = _user(
        db_session,
        prefix="RESPONSE-CLERK",
        permission_codes=("record_response",),
    )
    question = _question()
    db_session.add(question)
    db_session.commit()

    response = client.post(
        f"/records/{question.id}/response",
        json=_payload(),
        headers=_headers(db_session, clerk),
    )

    assert response.status_code == 201
    assert response.json()["record_id"] == str(question.id)
    assert response.json()["response_text"] == _payload()["response_text"]
    assert response.json()["response_date"] == "2026-09-14"
    persisted = db_session.query(models.QuestionResponse).one()
    assert persisted.response_text == _payload()["response_text"]
    assert persisted.response_date == date(2026, 9, 14)
    assert persisted.recorded_by == clerk.id


def test_non_clerk_permission_cannot_record_response(client, db_session):
    _load_response_service_module()
    member = _user(
        db_session,
        prefix="RESPONSE-MEMBER",
        permission_codes=("submit_question",),
    )
    question = _question()
    db_session.add(question)
    db_session.commit()

    response = client.post(
        f"/records/{question.id}/response",
        json=_payload(),
        headers=_headers(db_session, member),
    )

    assert response.status_code == 403


def test_response_endpoint_returns_not_found_for_unknown_question(
    client,
    db_session,
):
    _load_response_service_module()
    clerk = _user(
        db_session,
        prefix="RESPONSE-MISSING",
        permission_codes=("record_response",),
    )

    response = client.post(
        f"/records/{uuid4()}/response",
        json=_payload(),
        headers=_headers(db_session, clerk),
    )

    assert response.status_code == 404


def test_response_requires_scheduled_question_without_existing_response(
    client,
    db_session,
):
    _load_response_service_module()
    clerk = _user(
        db_session,
        prefix="RESPONSE-STATE",
        permission_codes=("record_response",),
    )
    unscheduled = _question(status="Approved")
    db_session.add(unscheduled)
    db_session.commit()

    invalid_state = client.post(
        f"/records/{unscheduled.id}/response",
        json=_payload(),
        headers=_headers(db_session, clerk),
    )

    assert invalid_state.status_code == 409

    scheduled = _question()
    db_session.add(scheduled)
    db_session.commit()
    first = client.post(
        f"/records/{scheduled.id}/response",
        json=_payload(),
        headers=_headers(db_session, clerk),
    )
    repeated = client.post(
        f"/records/{scheduled.id}/response",
        json=_payload(),
        headers=_headers(db_session, clerk),
    )

    assert first.status_code == 201
    assert repeated.status_code == 409
