from datetime import date, datetime, timedelta, timezone

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


def add_record(db_session, session, *, subject, full_text):
    record = ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Keyword Tester",
        ministry="Ministry of Testing",
        answer_type="Oral",
        subject=subject,
        full_text=full_text,
        status="Approved",
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_keyword_search_matches_subject_and_content_and_excludes_nonmatches(
    client,
    db_session,
):
    session = ParliamentarySession(
        code="KEYWORD-SEARCH-SESSION",
        name="Keyword Search Session",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status="Active",
    )
    user = User(
        employee_id="EMP-KEYWORD-SEARCH",
        name="Keyword Search User",
        role="Legacy",
        status="Active",
    )
    db_session.add_all([session, user])
    db_session.flush()
    subject_match = add_record(
        db_session,
        session,
        subject="Solargrid Expansion Programme",
        full_text=(
            "The programme will expand reliable electricity connections "
            "throughout rural districts during the next financial year."
        ),
    )
    content_match = add_record(
        db_session,
        session,
        subject="Rural Electrification Progress",
        full_text=(
            "The Ministry will report on Solargrid installations completed "
            "in underserved communities and the remaining implementation plan."
        ),
    )
    nonmatch = add_record(
        db_session,
        session,
        subject="Agricultural Storage Facilities",
        full_text=(
            "The Ministry will provide an update on grain storage capacity "
            "and crop marketing arrangements across provincial centres."
        ),
    )
    db_session.commit()

    response = client.post(
        "/search",
        json={"query_text": "SOLARGRID", "limit": 10},
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 200
    result_ids = {
        result["record"]["id"] for result in response.json()["results"]
    }
    assert result_ids == {str(subject_match.id), str(content_match.id)}
    assert str(nonmatch.id) not in result_ids
