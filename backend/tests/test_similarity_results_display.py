import importlib
import importlib.util
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

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
from app.similarity.base import SimilarityBackend, SimilarityMatch
from app.similarity.duplicate_detection import DuplicateMatch


def _load_presentation_module():
    qualified_name = "app.similarity.presentation"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-014 similarity presentation module has not been implemented"
    )
    return importlib.import_module(qualified_name)


class FakeSimilarityBackend(SimilarityBackend):
    def __init__(self, matches=()):
        self.matches = list(matches)

    def find_similar(
        self,
        text,
        threshold,
        top_n,
        *,
        exclude_ids=(),
        statuses=None,
        item_type=None,
    ):
        return self.matches[:top_n]


def _session(code, *, status="Closed"):
    return ParliamentarySession(
        code=code,
        name=f"{code} Parliament",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        status=status,
    )


def _record(session, *, member, subject, created_at):
    return ParliamentaryRecord(
        item_type="Question",
        session=session,
        member=member,
        ministry="Water Development",
        answer_type="Oral",
        subject=subject,
        full_text=f"{subject} with sufficient fixture content for validation.",
        status="Archived",
        created_at=created_at,
    )


def test_presenter_includes_required_source_context_and_rank_order(db_session):
    presentation = _load_presentation_module()
    older_session = _session("2024-SESSION")
    newer_session = _session("2025-SESSION")
    lower = _record(
        older_session,
        member="Hon. Lower Score",
        subject="Lower score matter",
        created_at=datetime(2024, 5, 2, tzinfo=timezone.utc),
    )
    higher = _record(
        newer_session,
        member="Hon. Higher Score",
        subject="Higher score matter",
        created_at=datetime(2025, 6, 3, tzinfo=timezone.utc),
    )
    db_session.add_all([lower, higher])
    db_session.commit()
    formatter = presentation.DatabaseSimilarityResultFormatter(db_session)

    results = formatter.format(
        [
            DuplicateMatch(lower.id, 0.96, "semantic"),
            DuplicateMatch(higher.id, 0.99, "semantic"),
        ]
    )

    assert [result.source_record for result in results] == [higher.id, lower.id]
    assert [result.rank for result in results] == [1, 2]
    assert results[0].session == newer_session.code
    assert results[0].date == date(2025, 6, 3)
    assert results[0].member_name == "Hon. Higher Score"
    assert results[0].source_id == higher.id


def _user(db_session):
    permission = Permission(
        code="submit_question",
        description="Submit questions",
    )
    user = User(
        employee_id=f"EMP-DISPLAY-{uuid4()}",
        name="Similarity Display User",
        role="Member",
        status="Active",
        roles=[Role(name=f"Display Role {uuid4()}", permissions=[permission])],
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


def _check_payload():
    return {
        "item_type": "Question",
        "subject": "Rural borehole construction progress",
        "full_text": (
            "What progress has been made on rural borehole construction "
            "during the current implementation period?"
        ),
    }


def test_similarity_check_api_returns_ranked_source_context(
    client,
    db_session,
):
    _load_presentation_module()
    dependencies = importlib.import_module("app.similarity.dependencies")
    first_session = _session("DISPLAY-FIRST")
    second_session = _session("DISPLAY-SECOND")
    lower = _record(
        first_session,
        member="Hon. First Member",
        subject="First historical matter",
        created_at=datetime(2024, 4, 1, tzinfo=timezone.utc),
    )
    higher = _record(
        second_session,
        member="Hon. Second Member",
        subject="Second historical matter",
        created_at=datetime(2025, 5, 2, tzinfo=timezone.utc),
    )
    user = _user(db_session)
    db_session.add_all([lower, higher])
    db_session.commit()
    app.dependency_overrides[dependencies.get_similarity_backend] = lambda: (
        FakeSimilarityBackend(
            [
                SimilarityMatch(lower.id, 0.96),
                SimilarityMatch(higher.id, 0.99),
            ]
        )
    )

    response = client.post(
        "/submissions/check-similarity",
        json=_check_payload(),
        headers=_headers(db_session, user),
    )

    assert response.status_code == 200
    matches = response.json()["matches"]
    assert [match["score"] for match in matches] == [0.99, 0.96]
    assert matches[0] == {
        "rank": 1,
        "score": 0.99,
        "match_type": "semantic",
        "session": second_session.code,
        "date": "2025-05-02",
        "member_name": "Hon. Second Member",
        "source_record": str(higher.id),
        "source_id": str(higher.id),
    }


def test_similarity_check_api_returns_well_formed_zero_matches(
    client,
    db_session,
):
    _load_presentation_module()
    dependencies = importlib.import_module("app.similarity.dependencies")
    user = _user(db_session)
    app.dependency_overrides[dependencies.get_similarity_backend] = lambda: (
        FakeSimilarityBackend()
    )

    response = client.post(
        "/submissions/check-similarity",
        json=_check_payload(),
        headers=_headers(db_session, user),
    )

    assert response.status_code == 200
    assert response.json() == {
        "possible_duplicate": False,
        "threshold": 0.95,
        "matches": [],
        "previously_addressed": [],
    }
