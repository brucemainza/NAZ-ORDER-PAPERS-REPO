import importlib
import importlib.util
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.email.base import EmailProvider
from app.lib.auth import create_access_token
from app.models import (
    BackgroundJob,
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)
from app.jobs.worker import claim_jobs, process_claimed_job
from app.notifications.service import NotificationService


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


def _user(db_session, *, prefix, permission_codes=(), email=None):
    permissions = [
        Permission(code=code, description=code.replace("_", " ").title())
        for code in permission_codes
    ]
    user = User(
        employee_id=f"{prefix}-{uuid4()}",
        name=f"{prefix} User",
        email=email,
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


def _question(*, status="Scheduled", submitter=None):
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
        submitter=submitter,
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


def test_response_idempotency_replays_original_and_rejects_changed_payload(
    client,
    db_session,
):
    models = importlib.import_module("app.models")
    clerk = _user(
        db_session,
        prefix="RESPONSE-IDEMPOTENT",
        permission_codes=("record_response",),
    )
    question = _question()
    db_session.add(question)
    db_session.commit()
    headers = {
        **_headers(db_session, clerk),
        "Idempotency-Key": "response-recording-001",
    }

    first = client.post(
        f"/records/{question.id}/response",
        json=_payload(),
        headers=headers,
    )
    replay = client.post(
        f"/records/{question.id}/response",
        json=_payload(),
        headers=headers,
    )
    conflict = client.post(
        f"/records/{question.id}/response",
        json={**_payload(), "response_date": "2026-09-15"},
        headers=headers,
    )

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert db_session.query(models.QuestionResponse).count() == 1


class FakeEmailProvider(EmailProvider):
    def __init__(self):
        self.calls = []

    async def send_email(
        self,
        to,
        subject,
        body,
        html_body=None,
    ):
        self.calls.append(
            {
                "to": to,
                "subject": subject,
                "body": body,
                "html_body": html_body,
            }
        )
        return True


def test_recording_response_marks_question_answered_and_queues_notification(
    client,
    db_session,
):
    _load_response_service_module()
    email_factory = importlib.import_module("app.email.factory")
    provider = FakeEmailProvider()
    app = importlib.import_module("app.main").app
    app.dependency_overrides[email_factory.get_email_provider] = lambda: provider
    clerk = _user(
        db_session,
        prefix="ANSWERED-CLERK",
        permission_codes=("record_response",),
    )
    submitter = _user(
        db_session,
        prefix="ANSWERED-SUBMITTER",
        email="answered.submitter@parliament.gov.zm",
    )
    question = _question(submitter=submitter)
    db_session.add(question)
    db_session.commit()

    response = client.post(
        f"/records/{question.id}/response",
        json=_payload(),
        headers=_headers(db_session, clerk),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "Answered"
    db_session.refresh(question)
    assert question.status == "Answered"
    assert provider.calls == []
    job = db_session.query(BackgroundJob).filter_by(job_type="notification").one()
    claim_jobs(db_session, worker_id="response-mail-worker", limit=1)
    db_session.commit()

    assert process_claimed_job(
        job.id,
        notifier=NotificationService(provider),
    ) is True
    assert len(provider.calls) == 1
    assert provider.calls[0]["to"] == "answered.submitter@parliament.gov.zm"
    assert provider.calls[0]["subject"] == (
        "Question status changed to Answered"
    )


class FailingStatusTransitioner:
    def transition(self, record, target_status):
        raise RuntimeError("forced status update failure")


def test_response_and_status_transition_are_atomic_on_forced_failure(db_session):
    responses = _load_response_service_module()
    models = importlib.import_module("app.models")
    clerk = _user(
        db_session,
        prefix="ATOMIC-CLERK",
        permission_codes=("record_response",),
    )
    question = _question()
    db_session.add(question)
    db_session.commit()
    service = responses.ResponseRecordingService(
        db_session,
        status_transitioner=FailingStatusTransitioner(),
    )

    with pytest.raises(RuntimeError, match="forced status update failure"):
        service.record_response(
            record_id=question.id,
            response_text=_payload()["response_text"],
            response_date=date(2026, 9, 14),
            recorded_by=clerk.id,
        )

    assert db_session.query(models.QuestionResponse).count() == 0
    assert db_session.query(BackgroundJob).filter_by(job_type="notification").count() == 0
    db_session.refresh(question)
    assert question.status == "Scheduled"
