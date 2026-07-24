from datetime import date, datetime, timedelta, timezone

import pytest

from app.lib.auth import create_access_token
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)


def create_record(db_session, status="Under Review"):
    session = ParliamentarySession(
        code="TEST-WORKFLOW-SESSION",
        name="Workflow Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    record = ParliamentaryRecord(
        item_type="Motion",
        session=session,
        member="Hon. Workflow Member",
        subject="Rural infrastructure maintenance",
        full_text=(
            "That this House urges the Government to expand routine "
            "maintenance of rural public infrastructure."
        ),
        status=status,
    )
    db_session.add(record)
    db_session.commit()
    return record


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


@pytest.mark.parametrize(
    ("action", "permission", "expected_status"),
    [
        ("Approve", "approve_motion", "Approved"),
        ("Reject", "reject_submission", "Rejected"),
        ("Request Changes", "request_changes", "Draft"),
    ],
)
def test_workflow_action_transitions_status_with_relevant_permission(
    client,
    db_session,
    action,
    permission,
    expected_status,
):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        f"EMP-{permission.upper()}",
        permission,
    )

    response = client.post(
        f"/submissions/{record.id}/workflow-review",
        json={"action": action, "notes": f"{action} test notes"},
        headers=auth_headers(db_session, reviewer),
    )

    assert response.status_code == 201
    assert response.json()["action"] == action
    assert response.json()["status"] == expected_status
    db_session.refresh(record)
    assert record.status == expected_status


@pytest.mark.parametrize(
    "action",
    ["Approve", "Reject", "Request Changes"],
)
def test_workflow_action_requires_its_relevant_permission(
    client,
    db_session,
    action,
):
    record = create_record(db_session)
    reviewer = create_user(db_session, f"EMP-NO-{action.replace(' ', '-').upper()}")

    response = client.post(
        f"/submissions/{record.id}/workflow-review",
        json={"action": action},
        headers=auth_headers(db_session, reviewer),
    )

    assert response.status_code == 403
    db_session.refresh(record)
    assert record.status == "Under Review"


def test_similarity_classification_does_not_change_workflow_status(
    client,
    db_session,
):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        "EMP-SIMILARITY-REVIEWER",
        "review_submission",
    )

    response = client.post(
        f"/records/{record.id}/reviews",
        json={"decision": "Clear (New)", "notes": "No prior match"},
        headers=auth_headers(db_session, reviewer),
    )

    assert response.status_code == 201
    db_session.refresh(record)
    assert record.status == "Under Review"
