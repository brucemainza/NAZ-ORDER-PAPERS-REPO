import ast
import asyncio
import importlib
import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.email.base import EmailProvider
from app.lib.auth import create_access_token
from app.main import app
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)


def _load_notification_module():
    qualified_name = "app.notifications.service"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-031 NotificationService has not been implemented"
    )
    return importlib.import_module(qualified_name)


class FakeEmailProvider(EmailProvider):
    def __init__(self, *, result=True, error=None):
        self.result = result
        self.error = error
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
        if self.error is not None:
            raise self.error
        return self.result


def _notification_args(**overrides):
    values = {
        "recipient": "member@parliament.gov.zm",
        "record_id": uuid4(),
        "item_type": "Question",
        "subject": "Rural borehole progress",
        "old_status": "Scheduled",
        "new_status": "Answered",
    }
    values.update(overrides)
    return values


def test_notification_service_calls_substitutable_provider_with_correct_message():
    notifications = _load_notification_module()
    provider = FakeEmailProvider()
    service = notifications.NotificationService(provider)

    sent = asyncio.run(
        service.notify_status_change(**_notification_args())
    )

    assert sent is True
    assert len(provider.calls) == 1
    assert provider.calls[0]["to"] == "member@parliament.gov.zm"
    assert provider.calls[0]["subject"] == (
        "Question status changed to Answered"
    )
    assert "Rural borehole progress" in provider.calls[0]["body"]
    assert "Scheduled" in provider.calls[0]["body"]
    assert "Answered" in provider.calls[0]["body"]


def test_notification_service_logs_failure_without_raising(caplog):
    notifications = _load_notification_module()
    provider = FakeEmailProvider(error=RuntimeError("provider unavailable"))
    service = notifications.NotificationService(provider)

    sent = asyncio.run(
        service.notify_status_change(**_notification_args())
    )

    assert sent is False
    assert "status-change email failed" in caplog.text


def test_notification_service_does_not_send_when_status_is_unchanged():
    notifications = _load_notification_module()
    provider = FakeEmailProvider()
    service = notifications.NotificationService(provider)

    sent = asyncio.run(
        service.notify_status_change(
            **_notification_args(
                old_status="Scheduled",
                new_status="Scheduled",
            )
        )
    )

    assert sent is True
    assert provider.calls == []


def _session():
    return ParliamentarySession(
        code=f"NOTIFY-{uuid4()}",
        name="Notification Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )


def _user(db_session, *, employee_prefix, permission_codes=(), email=None):
    permissions = [
        Permission(code=code, description=code.replace("_", " ").title())
        for code in permission_codes
    ]
    user = User(
        employee_id=f"{employee_prefix}-{uuid4()}",
        name=f"{employee_prefix} User",
        role="Member",
        status="Active",
        email=email,
        roles=[
            Role(
                name=f"{employee_prefix} Role {uuid4()}",
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


def test_status_change_endpoint_sends_exactly_one_background_email(
    client,
    db_session,
):
    _load_notification_module()
    email_factory = importlib.import_module("app.email.factory")
    provider = FakeEmailProvider()
    app.dependency_overrides[email_factory.get_email_provider] = lambda: provider
    submitter = _user(
        db_session,
        employee_prefix="NOTIFY-SUBMITTER",
        email="submitter@parliament.gov.zm",
    )
    scheduler = _user(
        db_session,
        employee_prefix="NOTIFY-SCHEDULER",
        permission_codes=("schedule_item",),
    )
    record = ParliamentaryRecord(
        item_type="Question",
        session=_session(),
        member="Hon. Notification Member",
        ministry="Water Development",
        answer_type="Oral",
        subject="Notification integration question",
        full_text=(
            "What is the status of the notification integration question "
            "during the current parliamentary session?"
        ),
        status="Approved",
        submitter=submitter,
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-02"},
        headers=_headers(db_session, scheduler),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Scheduled"
    assert len(provider.calls) == 1
    assert provider.calls[0]["to"] == "submitter@parliament.gov.zm"
    assert provider.calls[0]["subject"] == (
        "Question status changed to Scheduled"
    )


def test_email_failure_does_not_roll_back_status_change(client, db_session):
    _load_notification_module()
    email_factory = importlib.import_module("app.email.factory")
    provider = FakeEmailProvider(error=RuntimeError("mail unavailable"))
    app.dependency_overrides[email_factory.get_email_provider] = lambda: provider
    submitter = _user(
        db_session,
        employee_prefix="FAIL-SUBMITTER",
        email="failure@parliament.gov.zm",
    )
    scheduler = _user(
        db_session,
        employee_prefix="FAIL-SCHEDULER",
        permission_codes=("schedule_item",),
    )
    record = ParliamentaryRecord(
        item_type="Question",
        session=_session(),
        member="Hon. Failure Member",
        ministry="Water Development",
        answer_type="Written",
        subject="Failure isolation question",
        full_text=(
            "What is the status of the failure isolation question during "
            "the current parliamentary session?"
        ),
        status="Approved",
        submitter=submitter,
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-03"},
        headers=_headers(db_session, scheduler),
    )

    assert response.status_code == 200
    db_session.refresh(record)
    assert record.status == "Scheduled"
    assert len(provider.calls) == 1


def test_non_status_draft_update_sends_no_email(client, db_session):
    _load_notification_module()
    email_factory = importlib.import_module("app.email.factory")
    provider = FakeEmailProvider()
    app.dependency_overrides[email_factory.get_email_provider] = lambda: provider
    submitter = _user(
        db_session,
        employee_prefix="UNCHANGED-SUBMITTER",
        permission_codes=("submit_question",),
        email="unchanged@parliament.gov.zm",
    )
    record = ParliamentaryRecord(
        item_type="Question",
        session=_session(),
        member="Hon. Unchanged Member",
        ministry="Water Development",
        answer_type="Oral",
        subject="Original unchanged-status subject",
        full_text=(
            "What is the original unchanged-status question for the current "
            "parliamentary session and implementation period?"
        ),
        status="Draft",
        submitter=submitter,
    )
    db_session.add(record)
    db_session.commit()

    response = client.patch(
        f"/submissions/{record.id}",
        json={"subject": "Revised unchanged-status subject"},
        headers=_headers(db_session, submitter),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Draft"
    assert provider.calls == []


def test_application_code_does_not_import_concrete_email_provider():
    app_root = Path(__file__).parents[1] / "app"
    violations = []
    for path in app_root.rglob("*.py"):
        if path.parent == app_root / "email":
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == (
                "app.email.smtp_provider"
            ):
                violations.append(str(path.relative_to(app_root)))
            if isinstance(node, ast.Import):
                if any(
                    alias.name == "app.email.smtp_provider"
                    for alias in node.names
                ):
                    violations.append(str(path.relative_to(app_root)))

    assert violations == []
