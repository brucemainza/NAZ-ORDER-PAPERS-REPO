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


def _load_previously_addressed_module():
    qualified_name = "app.similarity.previously_addressed"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-016 previously-addressed service has not been implemented"
    )
    return importlib.import_module(qualified_name)


class FakeSimilarityBackend(SimilarityBackend):
    def __init__(self, matches=()):
        self.matches = list(matches)
        self.calls = []

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
        self.calls.append(
            {
                "text": text,
                "threshold": threshold,
                "top_n": top_n,
                "statuses": tuple(statuses) if statuses is not None else None,
                "item_type": item_type,
            }
        )
        return [
            match for match in self.matches if match.score >= threshold
        ][:top_n]


def _session(code, start_year):
    return ParliamentarySession(
        code=f"{code}-{uuid4()}",
        name=f"{code} Session",
        start_date=date(start_year, 1, 1),
        end_date=date(start_year, 12, 31),
        status="Closed" if start_year < 2026 else "Active",
    )


def _record(session, *, status, subject):
    return ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Historical Member",
        ministry="Water Development",
        answer_type="Oral",
        subject=subject,
        full_text=f"{subject} with enough historical matter fixture detail.",
        status=status,
    )


def test_similar_answered_item_from_prior_session_is_surfaced(db_session):
    previously_addressed = _load_previously_addressed_module()
    old_session = _session("OLD", 2025)
    current_session = _session("CURRENT", 2026)
    answered = _record(
        old_session,
        status="Answered",
        subject="Rural borehole construction",
    )
    db_session.add_all([answered, current_session])
    db_session.commit()
    backend = FakeSimilarityBackend(
        [SimilarityMatch(source_id=answered.id, score=0.84)]
    )
    service = previously_addressed.PreviouslyAddressedService(
        db_session,
        backend,
    )

    result = service.check(
        subject="Rural water infrastructure",
        full_text="What progress has been made on rural borehole construction?",
        item_type="Question",
        current_session_id=current_session.id,
    )

    assert result.matches == [
        previously_addressed.PreviouslyAddressedMatch(
            source_id=answered.id,
            score=0.84,
        )
    ]
    assert backend.calls == [
        {
            "text": (
                "Rural water infrastructure\n"
                "What progress has been made on rural borehole construction?"
            ),
            "threshold": 0.72,
            "top_n": 15,
            "statuses": ("Answered", "Discussed"),
            "item_type": "Question",
        }
    ]


def test_unanswered_or_current_session_items_are_not_previously_addressed(
    db_session,
):
    previously_addressed = _load_previously_addressed_module()
    old_session = _session("OLD-UNANSWERED", 2025)
    current_session = _session("CURRENT-ANSWERED", 2026)
    unanswered = _record(
        old_session,
        status="Approved",
        subject="Unanswered rural water matter",
    )
    current_answered = _record(
        current_session,
        status="Answered",
        subject="Current session rural water matter",
    )
    db_session.add_all([unanswered, current_answered])
    db_session.commit()
    backend = FakeSimilarityBackend(
        [
            SimilarityMatch(source_id=unanswered.id, score=0.90),
            SimilarityMatch(source_id=current_answered.id, score=0.89),
        ]
    )
    service = previously_addressed.PreviouslyAddressedService(
        db_session,
        backend,
    )

    result = service.check(
        subject="Rural water infrastructure",
        full_text="What progress has been made on rural water infrastructure?",
        item_type="Question",
        current_session_id=current_session.id,
    )

    assert result.matches == []


def _user(db_session):
    permission = Permission(
        code="submit_question",
        description="Submit questions",
    )
    user = User(
        employee_id=f"EMP-ADDRESSED-{uuid4()}",
        name="Previously Addressed User",
        role="Member",
        status="Active",
        roles=[Role(name=f"Addressed Role {uuid4()}", permissions=[permission])],
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


def test_similarity_check_api_surfaces_previously_answered_matter(
    client,
    db_session,
):
    _load_previously_addressed_module()
    dependencies = importlib.import_module("app.similarity.dependencies")
    old_session = _session("API-OLD", 2025)
    current_session = _session("API-CURRENT", 2026)
    answered = _record(
        old_session,
        status="Answered",
        subject="Rural borehole construction",
    )
    user = _user(db_session)
    db_session.add_all([answered, current_session])
    db_session.commit()
    app.dependency_overrides[dependencies.get_similarity_backend] = lambda: (
        FakeSimilarityBackend(
            [SimilarityMatch(source_id=answered.id, score=0.84)]
        )
    )

    response = client.post(
        "/submissions/check-similarity",
        json={
            "item_type": "Question",
            "session_id": str(current_session.id),
            "subject": "Rural water infrastructure",
            "full_text": (
                "What progress has been made on rural borehole construction "
                "during the current implementation period?"
            ),
        },
        headers=_headers(db_session, user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["possible_duplicate"] is False
    assert payload["matches"] == []
    assert payload["previously_addressed"][0]["source_record"] == str(answered.id)
    assert payload["previously_addressed"][0]["match_type"] == (
        "previously_addressed"
    )
