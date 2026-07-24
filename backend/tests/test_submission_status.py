from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.lib.auth import create_access_token
from app.models import ParliamentaryRecord, ParliamentarySession, Permission, Role, User, UserSession
from app.services.submission_status import (
    ALLOWED_TRANSITIONS,
    InvalidStatusTransition,
    SubmissionStatus,
    transition_submission,
)


def test_supported_status_enum_is_exact():
    assert {status.value for status in SubmissionStatus} == {
        "Draft",
        "Submitted",
        "Under Review",
        "Approved",
        "Rejected",
        "Scheduled",
        "Answered",
        "Discussed",
        "Archived",
    }


def test_status_state_machine_has_expected_transitions():
    assert ALLOWED_TRANSITIONS == {
        SubmissionStatus.DRAFT: {
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.ARCHIVED,
        },
        SubmissionStatus.SUBMITTED: {
            SubmissionStatus.UNDER_REVIEW,
            SubmissionStatus.ARCHIVED,
        },
        SubmissionStatus.UNDER_REVIEW: {
            SubmissionStatus.DRAFT,
            SubmissionStatus.APPROVED,
            SubmissionStatus.REJECTED,
            SubmissionStatus.ARCHIVED,
        },
        SubmissionStatus.APPROVED: {
            SubmissionStatus.SCHEDULED,
            SubmissionStatus.ARCHIVED,
        },
        SubmissionStatus.REJECTED: {SubmissionStatus.ARCHIVED},
        SubmissionStatus.SCHEDULED: {
            SubmissionStatus.ANSWERED,
            SubmissionStatus.DISCUSSED,
            SubmissionStatus.ARCHIVED,
        },
        SubmissionStatus.ANSWERED: {SubmissionStatus.ARCHIVED},
        SubmissionStatus.DISCUSSED: {SubmissionStatus.ARCHIVED},
        SubmissionStatus.ARCHIVED: set(),
    }


def test_invalid_transition_is_rejected_without_changing_status():
    submission = SimpleNamespace(status="Draft")

    with pytest.raises(InvalidStatusTransition, match="Draft.*Scheduled"):
        transition_submission(submission, SubmissionStatus.SCHEDULED)

    assert submission.status == "Draft"


def create_draft_context(db_session):
    session = ParliamentarySession(
        code="TEST-STATUS-SESSION",
        name="Status Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    permission = Permission(
        code="submit_question",
        description="Submit questions",
    )
    owner = User(
        employee_id="EMP-STATUS-OWNER",
        name="Status Owner",
        role="Viewer",
        status="Active",
        roles=[Role(name="Status Owner Role", permissions=[permission])],
    )
    other_user = User(
        employee_id="EMP-STATUS-OTHER",
        name="Status Other User",
        role="Viewer",
        status="Active",
    )
    record = ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Status Member",
        ministry="Ministry of Finance",
        answer_type="Written",
        subject="Status resubmission question",
        full_text=(
            "What measures will the Ministry take to address this status "
            "resubmission question during the current session?"
        ),
        status="Draft",
        submitter=owner,
    )
    db_session.add_all([record, other_user])
    db_session.commit()
    return record, owner, other_user


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


def test_owner_can_resubmit_draft_through_submitted_to_under_review(
    client,
    db_session,
):
    record, owner, _other_user = create_draft_context(db_session)

    response = client.post(
        f"/submissions/{record.id}/submit",
        headers=auth_headers(db_session, owner),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Under Review"
    db_session.refresh(record)
    assert record.status == "Under Review"


def test_non_owner_cannot_resubmit_draft(client, db_session):
    record, _owner, other_user = create_draft_context(db_session)

    response = client.post(
        f"/submissions/{record.id}/submit",
        headers=auth_headers(db_session, other_user),
    )

    assert response.status_code == 403
    db_session.refresh(record)
    assert record.status == "Draft"


def test_owner_can_edit_draft_before_resubmitting(client, db_session):
    record, owner, _other_user = create_draft_context(db_session)

    response = client.patch(
        f"/submissions/{record.id}",
        json={
            "subject": "Revised status resubmission question",
            "full_text": (
                "What revised measures will the Ministry take to address "
                "this resubmission question during the current session?"
            ),
        },
        headers=auth_headers(db_session, owner),
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Revised status resubmission question"
    db_session.refresh(record)
    assert record.subject == "Revised status resubmission question"


def test_non_owner_cannot_edit_draft(client, db_session):
    record, _owner, other_user = create_draft_context(db_session)

    response = client.patch(
        f"/submissions/{record.id}",
        json={"subject": "Unauthorized revision attempt"},
        headers=auth_headers(db_session, other_user),
    )

    assert response.status_code == 403
