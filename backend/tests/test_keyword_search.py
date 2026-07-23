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
    content_result = next(
        result
        for result in response.json()["results"]
        if result["record"]["id"] == str(content_match.id)
    )
    assert "Solargrid installations" in content_result["record"]["full_text"]
    assert content_result["matched_terms"] == ["solargrid"]

    paged_response = client.post(
        "/search",
        json={"query_text": "solargrid", "limit": 1, "offset": 1},
        headers=auth_headers(db_session, user),
    )
    assert paged_response.status_code == 200
    assert paged_response.json()["total_results"] == 2
    assert len(paged_response.json()["results"]) == 1
    assert paged_response.json()["results"][0]["rank"] == 2


def test_keyword_search_applies_all_browse_filters_before_bm25_ranking(
    client,
    db_session,
):
    first_session = ParliamentarySession(
        code="FILTERED-KEYWORD-SESSION-A",
        name="Filtered Keyword Session A",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status="Active",
    )
    second_session = ParliamentarySession(
        code="FILTERED-KEYWORD-SESSION-B",
        name="Filtered Keyword Session B",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status="Active",
    )
    user = User(
        employee_id="EMP-FILTERED-KEYWORD",
        name="Filtered Keyword User",
        role="Legacy",
        status="Active",
    )
    target = ParliamentaryRecord(
        item_type="Question",
        session=first_session,
        member="Hon. Alice Mulenga",
        ministry="Ministry of Water",
        answer_type="Written",
        subject="Rural Infrastructure Programme",
        full_text=(
            "The complete Waternetwork implementation details are contained "
            "inside this parliamentary question rather than its subject."
        ),
        status="Approved",
        created_at=datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),
    )
    wrong_member_and_status = ParliamentaryRecord(
        item_type="Question",
        session=first_session,
        member="Hon. Brian Zulu",
        ministry="Ministry of Agriculture",
        answer_type="Written",
        subject="Agricultural Infrastructure",
        full_text=(
            "This unrelated department also mentions Waternetwork so the "
            "record filters must run before relevance ranking."
        ),
        status="Rejected",
        created_at=datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc),
    )
    wrong_session = ParliamentaryRecord(
        item_type="Question",
        session=second_session,
        member="Hon. Alice Mulenga",
        ministry="Ministry of Water",
        answer_type="Written",
        subject="Other Session Infrastructure",
        full_text=(
            "Waternetwork content in a different session must not appear "
            "when the session filter is active."
        ),
        status="Approved",
        created_at=datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc),
    )
    wrong_date = ParliamentaryRecord(
        item_type="Question",
        session=first_session,
        member="Hon. Alice Mulenga",
        ministry="Ministry of Water",
        answer_type="Written",
        subject="Later Rural Infrastructure Programme",
        full_text=(
            "This Waternetwork content matches every filter except the "
            "requested record creation date."
        ),
        status="Approved",
        created_at=datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc),
    )
    db_session.add_all(
        [
            first_session,
            second_session,
            user,
            target,
            wrong_member_and_status,
            wrong_session,
            wrong_date,
        ]
    )
    db_session.commit()

    response = client.post(
        "/search",
        json={
            "query_text": "waternetwork",
            "session_id": str(first_session.id),
            "date": "2026-09-10",
            "member": "alice",
            "ministry": "water",
            "status": "Approved",
            "item_type": "Question",
            "limit": 15,
            "offset": 0,
        },
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 200
    assert response.json()["total_candidates"] == 1
    assert response.json()["total_results"] == 1
    assert [result["record"]["id"] for result in response.json()["results"]] == [
        str(target.id)
    ]
