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


def _load_session_report_module():
    qualified_name = "app.reports.session_report"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-037 session report service has not been implemented"
    )
    return importlib.import_module(qualified_name)


def _session(code, year):
    return ParliamentarySession(
        code=f"{code}-{uuid4()}",
        name=f"{code} Parliamentary Session",
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
        status="Closed" if year < 2026 else "Active",
    )


def _record(session, *, item_type, subject, status):
    return ParliamentaryRecord(
        item_type=item_type,
        session=session,
        member=f"Hon. {subject}",
        ministry="Water Development" if item_type == "Question" else None,
        answer_type="Oral" if item_type == "Question" else None,
        subject=subject,
        full_text=f"{subject} with sufficient session report fixture detail.",
        status=status,
    )


def _report_user(db_session):
    permission = Permission(code="view_reports", description="View reports")
    user = User(
        employee_id=f"EMP-SESSION-REPORT-{uuid4()}",
        name="Session Report User",
        role="Clerk",
        status="Active",
        roles=[
            Role(
                name=f"Session Report Role {uuid4()}",
                permissions=[permission],
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


def test_session_report_includes_only_selected_session_items_and_statuses(
    client,
    db_session,
):
    _load_session_report_module()
    selected = _session("SELECTED", 2026)
    other = _session("OTHER", 2025)
    answered_question = _record(
        selected,
        item_type="Question",
        subject="Answered water question",
        status="Answered",
    )
    pending_motion = _record(
        selected,
        item_type="Motion",
        subject="Pending roads motion",
        status="Under Review",
    )
    excluded = _record(
        other,
        item_type="Question",
        subject="Excluded health question",
        status="Archived",
    )
    user = _report_user(db_session)
    db_session.add_all([answered_question, pending_motion, excluded])
    db_session.commit()

    response = client.get(
        f"/reports/sessions/{selected.id}",
        headers=_headers(db_session, user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["id"] == str(selected.id)
    assert payload["summary"] == {
        "total": 2,
        "questions": 1,
        "motions": 1,
    }
    assert {item["id"] for item in payload["items"]} == {
        str(answered_question.id),
        str(pending_motion.id),
    }
    assert {
        item["subject"]: item["status"] for item in payload["items"]
    } == {
        "Answered water question": "Answered",
        "Pending roads motion": "Under Review",
    }
    assert str(excluded.id) not in {
        item["id"] for item in payload["items"]
    }


def test_empty_session_report_is_well_formed(client, db_session):
    _load_session_report_module()
    empty_session = _session("EMPTY", 2026)
    user = _report_user(db_session)
    db_session.add(empty_session)
    db_session.commit()

    response = client.get(
        f"/reports/sessions/{empty_session.id}",
        headers=_headers(db_session, user),
    )

    assert response.status_code == 200
    assert response.json()["summary"] == {
        "total": 0,
        "questions": 0,
        "motions": 0,
    }
    assert response.json()["items"] == []


def test_session_report_returns_not_found_for_unknown_session(
    client,
    db_session,
):
    _load_session_report_module()
    user = _report_user(db_session)

    response = client.get(
        f"/reports/sessions/{uuid4()}",
        headers=_headers(db_session, user),
    )

    assert response.status_code == 404
