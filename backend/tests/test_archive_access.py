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


def create_user(db_session, employee_id, permission_codes=()):
    permissions = [
        Permission(code=code, description=f"Permission {code}")
        for code in permission_codes
    ]
    role = Role(
        name=f"Custom Role {employee_id}",
        permissions=permissions,
    )
    user = User(
        employee_id=employee_id,
        name=f"Archive User {employee_id}",
        role="Legacy",
        roles=[role],
        status="Active",
    )
    db_session.add(user)
    db_session.flush()
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


def create_archived_record(db_session):
    session = ParliamentarySession(
        code="ARCHIVE-ACCESS-SESSION",
        name="Archive Access Session",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status="Active",
    )
    record = ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Archive Reader",
        ministry="Ministry of Records",
        answer_type="Written",
        subject="Copperarchive Historical Policy",
        full_text=(
            "Copperarchive appears in this archived parliamentary content "
            "to provide a deterministic archive search match."
        ),
        status="Archived",
    )
    db_session.add(record)
    db_session.commit()
    return record


def test_view_archive_permission_controls_archived_list_and_detail(
    client,
    db_session,
):
    record = create_archived_record(db_session)
    allowed = create_user(
        db_session,
        "EMP-ARCHIVE-VIEW",
        permission_codes=("view_archive",),
    )
    denied = create_user(db_session, "EMP-ARCHIVE-NO-VIEW")
    allowed_headers = auth_headers(db_session, allowed)
    denied_headers = auth_headers(db_session, denied)

    allowed_list = client.get("/records?status=Archived", headers=allowed_headers)
    denied_list = client.get("/records?status=Archived", headers=denied_headers)
    allowed_detail = client.get(f"/records/{record.id}", headers=allowed_headers)
    denied_detail = client.get(f"/records/{record.id}", headers=denied_headers)

    assert allowed_list.status_code == 200
    assert [item["id"] for item in allowed_list.json()] == [str(record.id)]
    assert denied_list.status_code == 200
    assert denied_list.json() == []
    assert allowed_detail.status_code == 200
    assert denied_detail.status_code == 403


def test_search_archive_permission_controls_archived_search_results(
    client,
    db_session,
):
    record = create_archived_record(db_session)
    allowed = create_user(
        db_session,
        "EMP-ARCHIVE-SEARCH",
        permission_codes=("search_archive",),
    )
    denied = create_user(db_session, "EMP-ARCHIVE-NO-SEARCH")
    allowed_headers = auth_headers(db_session, allowed)
    denied_headers = auth_headers(db_session, denied)
    request_body = {"query_text": "copperarchive", "limit": 10}

    allowed_response = client.post(
        "/search",
        json=request_body,
        headers=allowed_headers,
    )
    denied_response = client.post(
        "/search",
        json=request_body,
        headers=denied_headers,
    )

    assert allowed_response.status_code == 200
    assert [
        result["record"]["id"]
        for result in allowed_response.json()["results"]
    ] == [str(record.id)]
    assert denied_response.status_code == 200
    assert denied_response.json()["results"] == []
