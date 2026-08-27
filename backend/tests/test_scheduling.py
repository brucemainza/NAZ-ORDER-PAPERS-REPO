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


def create_record(db_session, status="Approved"):
    session = ParliamentarySession(
        code="TEST-SCHEDULING-SESSION",
        name="Scheduling Test Session",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 8, 31),
        status="Active",
    )
    record = ParliamentaryRecord(
        item_type="Motion",
        session=session,
        member="Hon. Scheduling Member",
        subject="District infrastructure scheduling motion",
        full_text=(
            "That this House urges the Government to schedule district "
            "infrastructure maintenance for the next financial year."
        ),
        status=status,
    )
    db_session.add(record)
    db_session.commit()
    return record


def create_user(db_session, has_schedule_permission):
    permissions = []
    if has_schedule_permission:
        permissions.append(
            Permission(
                code="schedule_item",
                description="Schedule approved items",
            )
        )
    user = User(
        employee_id=(
            "EMP-SCHEDULER" if has_schedule_permission else "EMP-NON-SCHEDULER"
        ),
        name="Scheduling Clerk",
        role="Viewer",
        status="Active",
        roles=[Role(name="Scheduling Test Role", permissions=permissions)],
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


def test_approved_item_can_be_scheduled_for_sitting_date(
    client,
    db_session,
):
    record = create_record(db_session)
    scheduler = create_user(db_session, has_schedule_permission=True)

    response = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-02"},
        headers=auth_headers(db_session, scheduler),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Scheduled"
    assert response.json()["sitting_date"] == "2026-10-02"
    db_session.refresh(record)
    assert record.status == "Scheduled"
    assert record.sitting_date == date(2026, 10, 2)


def test_only_approved_item_can_be_scheduled(client, db_session):
    record = create_record(db_session, status="Under Review")
    scheduler = create_user(db_session, has_schedule_permission=True)

    response = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-02"},
        headers=auth_headers(db_session, scheduler),
    )

    assert response.status_code == 409
    db_session.refresh(record)
    assert record.status == "Under Review"
    assert record.sitting_date is None


def test_scheduling_requires_schedule_item_permission(client, db_session):
    record = create_record(db_session)
    user = create_user(db_session, has_schedule_permission=False)

    response = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-02"},
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 403
    db_session.refresh(record)
    assert record.status == "Approved"
    assert record.sitting_date is None


def test_sitting_date_must_be_within_the_records_session(client, db_session):
    record = create_record(db_session)
    scheduler = create_user(db_session, has_schedule_permission=True)

    response = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2028-01-01"},
        headers=auth_headers(db_session, scheduler),
    )

    assert response.status_code == 422
    db_session.refresh(record)
    assert record.status == "Approved"
    assert record.sitting_date is None


def test_scheduling_idempotency_replays_and_rejects_changed_date(client, db_session):
    record = create_record(db_session)
    scheduler = create_user(db_session, has_schedule_permission=True)
    scheduler.email = "idempotent.scheduler@parliament.gov.zm"
    record.submitter = scheduler
    db_session.commit()
    headers = {
        **auth_headers(db_session, scheduler),
        "Idempotency-Key": "schedule-record-001",
    }

    first = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-02"},
        headers=headers,
    )
    replay = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-02"},
        headers=headers,
    )
    conflict = client.post(
        f"/submissions/{record.id}/schedule",
        json={"sitting_date": "2026-10-03"},
        headers=headers,
    )

    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert conflict.status_code == 409
