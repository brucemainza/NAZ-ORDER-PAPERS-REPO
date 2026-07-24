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


def create_context(db_session):
    session = ParliamentarySession(
        code="TEST-OWNERSHIP-SESSION",
        name="Ownership Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    submit_permission = Permission(
        code="submit_question",
        description="Submit questions",
    )
    review_permission = Permission(
        code="review_submission",
        description="Review submissions",
    )
    owner = User(
        employee_id="EMP-OWNER-001",
        name="Submission Owner",
        role="Viewer",
        status="Active",
        roles=[Role(name="Owner Role", permissions=[submit_permission])],
    )
    other_user = User(
        employee_id="EMP-OWNER-002",
        name="Other Submitter",
        role="Viewer",
        status="Active",
        roles=[Role(name="Other Role", permissions=[submit_permission])],
    )
    reviewer = User(
        employee_id="EMP-OWNER-CLERK",
        name="Ownership Reviewer",
        role="Viewer",
        status="Active",
        roles=[Role(name="Ownership Reviewer Role", permissions=[review_permission])],
    )
    db_session.add_all([session, owner, other_user, reviewer])
    db_session.commit()
    return session, owner, other_user, reviewer


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


def question_payload(session_id, subject):
    return {
        "item_type": "Question",
        "answer_type": "Written",
        "session_id": str(session_id),
        "member": "Hon. Ownership Member",
        "ministry": "Ministry of Justice",
        "subject": subject,
        "full_text": (
            "What measures will the Ministry take concerning "
            f"{subject.lower()} during the current parliamentary session?"
        ),
    }


def submit_question(client, db_session, session, user, subject):
    response = client.post(
        "/submissions",
        json=question_payload(session.id, subject),
        headers=auth_headers(db_session, user),
    )
    assert response.status_code == 201
    return response.json()["record"]


def test_submitter_can_query_only_their_submissions_and_current_status(
    client,
    db_session,
):
    session, owner, other_user, _reviewer = create_context(db_session)
    owned = submit_question(
        client,
        db_session,
        session,
        owner,
        "Owner status tracking question",
    )
    submit_question(
        client,
        db_session,
        session,
        other_user,
        "Other status tracking question",
    )

    response = client.get(
        "/submissions/mine",
        headers=auth_headers(db_session, owner),
    )

    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [owned["id"]]
    assert response.json()[0]["submitted_by"] == str(owner.id)
    assert response.json()[0]["status"] == "Under Review"


def test_non_owner_cannot_retrieve_list_or_search_another_users_draft(
    client,
    db_session,
):
    session, owner, other_user, reviewer = create_context(db_session)
    owned = submit_question(
        client,
        db_session,
        session,
        owner,
        "Confidentialdrafttoken budget question",
    )
    record = db_session.get(ParliamentaryRecord, owned["id"])
    record.status = "Draft"
    db_session.commit()

    other_headers = auth_headers(db_session, other_user)
    detail_response = client.get(f"/records/{record.id}", headers=other_headers)
    list_response = client.get("/records", headers=other_headers)
    search_response = client.post(
        "/search",
        json={"query_text": "Confidentialdrafttoken"},
        headers=other_headers,
    )

    assert detail_response.status_code == 403
    assert str(record.id) not in [item["id"] for item in list_response.json()]
    assert search_response.status_code == 200
    assert search_response.json()["results"] == []

    owner_response = client.get(
        f"/records/{record.id}",
        headers=auth_headers(db_session, owner),
    )
    reviewer_response = client.get(
        f"/records/{record.id}",
        headers=auth_headers(db_session, reviewer),
    )

    assert owner_response.status_code == 200
    assert reviewer_response.status_code == 200
