from datetime import date, datetime, timedelta, timezone

from app.lib.auth import create_access_token
from app.models import ParliamentaryRecord, ParliamentarySession, User, UserSession


def create_context(db_session):
    session = ParliamentarySession(
        code="TEST-ORDER-PAPER-SESSION",
        name="Order Paper Test Session",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 8, 31),
        status="Active",
    )
    user = User(
        employee_id="EMP-ORDER-PAPER",
        name="Order Paper Reader",
        role="Viewer",
        status="Active",
    )
    db_session.add_all([session, user])
    db_session.commit()
    return session, user


def add_record(
    db_session,
    session,
    *,
    item_type,
    subject,
    sitting_date,
    created_at,
    status="Scheduled",
):
    record = ParliamentaryRecord(
        item_type=item_type,
        session=session,
        member=f"Hon. {subject}",
        ministry="Ministry of Testing" if item_type == "Question" else None,
        answer_type="Oral" if item_type == "Question" else None,
        subject=subject,
        full_text=(
            f"This is the complete parliamentary text for {subject}, "
            "included to verify deterministic Order Paper generation."
        ),
        status=status,
        sitting_date=sitting_date,
        created_at=created_at,
    )
    db_session.add(record)
    db_session.commit()
    return record


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


def test_order_paper_contains_exact_sitting_items_grouped_and_ordered(
    client,
    db_session,
):
    session, user = create_context(db_session)
    sitting_date = date(2026, 10, 2)
    earlier = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)
    later = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)

    question_later = add_record(
        db_session,
        session,
        item_type="Question",
        subject="Question Later",
        sitting_date=sitting_date,
        created_at=later,
    )
    motion = add_record(
        db_session,
        session,
        item_type="Motion",
        subject="Motion One",
        sitting_date=sitting_date,
        created_at=earlier,
    )
    question_earlier = add_record(
        db_session,
        session,
        item_type="Question",
        subject="Question Earlier",
        sitting_date=sitting_date,
        created_at=earlier,
    )
    add_record(
        db_session,
        session,
        item_type="Question",
        subject="Different Sitting",
        sitting_date=date(2026, 10, 3),
        created_at=earlier,
    )
    add_record(
        db_session,
        session,
        item_type="Motion",
        subject="Approved But Not Scheduled",
        sitting_date=sitting_date,
        created_at=earlier,
        status="Approved",
    )

    response = client.get(
        f"/order-papers/{sitting_date.isoformat()}",
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 200
    paper = response.json()
    assert paper["sitting_date"] == "2026-10-02"
    assert paper["total_items"] == 3
    assert [section["item_type"] for section in paper["sections"]] == [
        "Question",
        "Motion",
    ]
    assert [item["id"] for item in paper["sections"][0]["items"]] == [
        str(question_earlier.id),
        str(question_later.id),
    ]
    assert [item["id"] for item in paper["sections"][1]["items"]] == [
        str(motion.id)
    ]


def test_order_paper_for_date_without_scheduled_items_is_empty(
    client,
    db_session,
):
    _session, user = create_context(db_session)

    response = client.get(
        "/order-papers/2026-12-01",
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 200
    assert response.json()["total_items"] == 0
    assert [section["items"] for section in response.json()["sections"]] == [
        [],
        [],
    ]
