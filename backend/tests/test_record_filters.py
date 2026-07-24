from datetime import date, datetime, timedelta, timezone

import pytest

from app.lib.auth import create_access_token
from app.models import ParliamentaryRecord, ParliamentarySession, User, UserSession


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


def add_record(
    db_session,
    session,
    *,
    item_type,
    member,
    ministry,
    subject,
    status,
    created_at,
):
    record = ParliamentaryRecord(
        item_type=item_type,
        session=session,
        member=member,
        ministry=ministry,
        answer_type="Written" if item_type == "Question" else None,
        subject=subject,
        full_text=(
            f"This is the complete parliamentary submission text for {subject}, "
            "created to verify independent and combined record filtering."
        ),
        status=status,
        created_at=created_at,
    )
    db_session.add(record)
    db_session.flush()
    return record


@pytest.fixture
def filter_context(db_session):
    first_session = ParliamentarySession(
        code="FILTER-SESSION-A",
        name="Filter Session A",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status="Active",
    )
    second_session = ParliamentarySession(
        code="FILTER-SESSION-B",
        name="Filter Session B",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status="Active",
    )
    user = User(
        employee_id="EMP-RECORD-FILTER",
        name="Record Filter User",
        role="Legacy",
        status="Active",
    )
    db_session.add_all([first_session, second_session, user])
    db_session.flush()
    target = add_record(
        db_session,
        first_session,
        item_type="Question",
        member="Hon. Alice Mulenga",
        ministry="Ministry of Health",
        subject="Target Health Question",
        status="Approved",
        created_at=datetime(2026, 9, 10, 8, 30, tzinfo=timezone.utc),
    )
    other = add_record(
        db_session,
        first_session,
        item_type="Motion",
        member="Hon. Brian Zulu",
        ministry=None,
        subject="Education Infrastructure Motion",
        status="Rejected",
        created_at=datetime(2026, 9, 11, 9, 0, tzinfo=timezone.utc),
    )
    second_session_record = add_record(
        db_session,
        second_session,
        item_type="Question",
        member="Hon. Catherine Phiri",
        ministry="Ministry of Agriculture",
        subject="Agricultural Support Question",
        status="Submitted",
        created_at=datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc),
    )
    db_session.commit()
    return {
        "headers": auth_headers(db_session, user),
        "first_session": first_session,
        "second_session": second_session,
        "target": target,
        "other": other,
        "second_session_record": second_session_record,
    }


@pytest.mark.parametrize(
    ("query_factory", "expected_key"),
    [
        (lambda context: f"session_id={context['second_session'].id}", "second_session_record"),
        (lambda _context: "date=2026-09-10", "target"),
        (lambda _context: "member=alice", "target"),
        (lambda _context: "ministry=health", "target"),
        (lambda _context: "status=Rejected", "other"),
        (lambda _context: "item_type=Motion", "other"),
    ],
)
def test_each_record_filter_independently_narrows_results(
    client,
    filter_context,
    query_factory,
    expected_key,
):
    response = client.get(
        f"/records?{query_factory(filter_context)}",
        headers=filter_context["headers"],
    )

    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [
        str(filter_context[expected_key].id)
    ]


def test_record_filters_can_be_combined(client, filter_context):
    target = filter_context["target"]
    query = (
        f"session_id={filter_context['first_session'].id}"
        "&date=2026-09-10"
        "&member=alice"
        "&ministry=health"
        "&status=Approved"
        "&item_type=Question"
    )

    response = client.get(
        f"/records?{query}",
        headers=filter_context["headers"],
    )

    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [str(target.id)]


def test_mutually_exclusive_record_filters_return_empty_list(
    client,
    filter_context,
):
    response = client.get(
        "/records?member=alice&ministry=agriculture",
        headers=filter_context["headers"],
    )

    assert response.status_code == 200
    assert response.json() == []
