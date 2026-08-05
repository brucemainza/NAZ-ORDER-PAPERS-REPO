from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database import engine
from app.lib.auth import create_access_token
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    ReviewDecision,
    User,
    UserSession,
    WorkflowDecision,
)
from app.routers.workflow_reviews import review_submission
from app.schemas.review import WorkflowReviewCreate


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


def test_workflow_action_idempotency_replays_and_detects_payload_conflict(
    client,
    db_session,
):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        "EMP-IDEMPOTENT-WORKFLOW",
        "approve_motion",
    )
    headers = {
        **auth_headers(db_session, reviewer),
        "Idempotency-Key": "workflow-approval-001",
    }

    first = client.post(
        f"/submissions/{record.id}/workflow-review",
        json={"action": "Approve", "notes": "Reviewed once"},
        headers=headers,
    )
    replay = client.post(
        f"/submissions/{record.id}/workflow-review",
        json={"action": "Approve", "notes": "Reviewed once"},
        headers=headers,
    )
    conflict = client.post(
        f"/submissions/{record.id}/workflow-review",
        json={"action": "Approve", "notes": "Different payload"},
        headers=headers,
    )

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert conflict.status_code == 409


def test_concurrent_workflow_actions_produce_one_valid_transition(db_session):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        "EMP-CONCURRENT-WORKFLOW",
        "approve_motion",
    )
    barrier = Barrier(2)

    class _Notifier:
        async def notify_status_change(self, **_kwargs):
            return True

    def attempt_review():
        with Session(engine) as worker_db:
            worker_reviewer = worker_db.get(User, reviewer.id)
            barrier.wait()
            try:
                response = review_submission(
                    record_id=record.id,
                    review=WorkflowReviewCreate(action="Approve"),
                    request=Request(
                        {
                            "type": "http",
                            "method": "POST",
                            "path": "/",
                            "headers": [],
                            "client": ("127.0.0.1", 1234),
                        }
                    ),
                    background_tasks=BackgroundTasks(),
                    idempotency_key=None,
                    db=worker_db,
                    reviewer=worker_reviewer,
                    notifier=_Notifier(),
                )
                assert response.status == "Approved"
                return 201
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _index: attempt_review(), range(2)))

    assert outcomes == [201, 409]
    db_session.expire_all()
    assert db_session.get(ParliamentaryRecord, record.id).status == "Approved"
    assert db_session.query(WorkflowDecision).count() == 1


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


@pytest.mark.parametrize(
    "payload",
    [
        {"decision": "Duplicate"},
        {"decision": "Substantially Similar"},
    ],
)
def test_similarity_decision_requires_related_record(client, db_session, payload):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        f"EMP-RELATION-{payload['decision']}",
        "review_submission",
    )

    response = client.post(
        f"/records/{record.id}/reviews",
        json=payload,
        headers=auth_headers(db_session, reviewer),
    )

    assert response.status_code == 422


def test_clear_decision_prohibits_related_record_and_self_links(client, db_session):
    record = create_record(db_session)
    related = ParliamentaryRecord(
        item_type="Motion",
        session=record.session,
        member="Hon. Related Member",
        subject="Related rural infrastructure matter",
        full_text="That this House considers a separate infrastructure matter.",
        status="Archived",
    )
    db_session.add(related)
    db_session.commit()
    reviewer = create_user(
        db_session,
        "EMP-CLEAR-RELATION",
        "review_submission",
    )
    headers = auth_headers(db_session, reviewer)

    clear_with_related = client.post(
        f"/records/{record.id}/reviews",
        json={"decision": "Clear (New)", "similar_record_id": str(related.id)},
        headers=headers,
    )
    duplicate_self = client.post(
        f"/records/{record.id}/reviews",
        json={"decision": "Duplicate", "similar_record_id": str(record.id)},
        headers=headers,
    )

    assert clear_with_related.status_code == 422
    assert duplicate_self.status_code == 422


def test_similarity_review_idempotency_replays_original_decision(client, db_session):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        "EMP-IDEMPOTENT-SIMILARITY",
        "review_submission",
    )
    headers = {
        **auth_headers(db_session, reviewer),
        "Idempotency-Key": "similarity-review-001",
    }

    first = client.post(
        f"/records/{record.id}/reviews",
        json={"decision": "Clear (New)", "notes": "No match"},
        headers=headers,
    )
    replay = client.post(
        f"/records/{record.id}/reviews",
        json={"decision": "Clear (New)", "notes": "No match"},
        headers=headers,
    )
    conflict = client.post(
        f"/records/{record.id}/reviews",
        json={"decision": "Clear (New)", "notes": "Changed notes"},
        headers=headers,
    )

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert conflict.status_code == 409


def test_database_rejects_invalid_similarity_relationship(db_session):
    record = create_record(db_session)
    reviewer = create_user(
        db_session,
        "EMP-DB-REVIEW-INVARIANT",
        "review_submission",
    )
    db_session.add(
        ReviewDecision(
            record_id=record.id,
            similar_record_id=None,
            decision="Duplicate",
            is_duplicate=True,
            reviewer_id=reviewer.id,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
