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
from app.similarity.embeddings import TokenHashEmbeddingGenerator


def _load_duplicate_detection_module():
    qualified_name = "app.similarity.duplicate_detection"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-012 duplicate-detection service has not been implemented"
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
                "exclude_ids": tuple(exclude_ids),
                "statuses": statuses,
                "item_type": item_type,
            }
        )
        return self.matches[:top_n]


def _session(code="DUPLICATE-SESSION", status="Active"):
    return ParliamentarySession(
        code=f"{code}-{uuid4()}",
        name="Duplicate Detection Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=status,
    )


def _record(session, *, full_text, subject="Rural water programme"):
    return ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Existing Member",
        ministry="Water Development",
        answer_type="Oral",
        subject=subject,
        full_text=full_text,
        status="Archived",
    )


def test_exact_duplicate_is_detected_with_a_mocked_similarity_backend(db_session):
    duplicate_detection = _load_duplicate_detection_module()
    session = _session(status="Closed")
    text = "What progress has been made on rural borehole construction?"
    existing = _record(
        session,
        full_text=text,
        subject="Rural borehole construction",
    )
    db_session.add(existing)
    db_session.commit()
    backend = FakeSimilarityBackend()
    service = duplicate_detection.DuplicateDetectionService(db_session, backend)

    result = service.check(
        subject="Rural borehole construction",
        full_text=f"  {text.upper()}  ",
        item_type="Question",
    )

    assert result.is_duplicate is True
    assert result.matches[0].source_id == existing.id
    assert result.matches[0].score == 1.0
    assert result.matches[0].match_type == "exact"
    assert backend.calls[0]["threshold"] == 0.95


def test_near_duplicate_above_threshold_is_detected_via_backend(db_session):
    duplicate_detection = _load_duplicate_detection_module()
    source_id = uuid4()
    backend = FakeSimilarityBackend(
        [SimilarityMatch(source_id=source_id, score=0.97)]
    )
    service = duplicate_detection.DuplicateDetectionService(db_session, backend)

    result = service.check(
        subject="Rural borehole construction",
        full_text="What progress has been made on borehole construction?",
        item_type="Question",
    )

    assert result.is_duplicate is True
    assert result.matches == [
        duplicate_detection.DuplicateMatch(
            source_id=source_id,
            score=0.97,
            match_type="semantic",
            ranking_score=0.97,
            cosine_similarity=0.97,
        )
    ]


def test_distinct_item_is_not_flagged_by_duplicate_service(db_session):
    duplicate_detection = _load_duplicate_detection_module()
    backend = FakeSimilarityBackend()
    service = duplicate_detection.DuplicateDetectionService(db_session, backend)

    result = service.check(
        subject="Satellite communications",
        full_text="How will satellite communications coverage be expanded?",
        item_type="Question",
    )

    assert result.is_duplicate is False
    assert result.matches == []


def _submitter(db_session):
    permission = Permission(
        code="submit_question",
        description="Submit questions",
    )
    user = User(
        employee_id=f"EMP-DUP-{uuid4()}",
        name="Duplicate Submitter",
        role="Member",
        status="Active",
        roles=[Role(name=f"Duplicate Role {uuid4()}", permissions=[permission])],
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


def _payload(session, *, confirm_duplicate=False):
    return {
        "item_type": "Question",
        "session_id": str(session.id),
        "member": "Hon. Duplicate Submitter",
        "ministry": "Water Development",
        "answer_type": "Oral",
        "subject": "Rural borehole construction progress",
        "full_text": (
            "What progress has been made on rural borehole construction "
            "during the current implementation period?"
        ),
        "confirm_duplicate": confirm_duplicate,
    }


def test_create_returns_409_for_possible_duplicate_before_saving(
    client,
    db_session,
):
    _load_duplicate_detection_module()
    dependencies = importlib.import_module("app.similarity.dependencies")
    session = _session()
    existing = _record(
        session,
        full_text="Existing matter with a semantically similar meaning.",
    )
    user = _submitter(db_session)
    db_session.add(existing)
    db_session.commit()
    app.dependency_overrides[dependencies.get_similarity_backend] = lambda: (
        FakeSimilarityBackend(
            [SimilarityMatch(source_id=existing.id, score=0.98)]
        )
    )

    response = client.post(
        "/submissions",
        json=_payload(session),
        headers=_headers(db_session, user),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "possible_duplicate"
    assert response.json()["detail"]["matches"][0]["source_id"] == str(existing.id)
    assert db_session.query(ParliamentaryRecord).count() == 1


def test_duplicate_confirmation_override_allows_submission(
    client,
    db_session,
):
    _load_duplicate_detection_module()
    dependencies = importlib.import_module("app.similarity.dependencies")
    session = _session()
    existing = _record(
        session,
        full_text="Existing matter with a semantically similar meaning.",
    )
    user = _submitter(db_session)
    db_session.add(existing)
    db_session.commit()
    app.dependency_overrides[dependencies.get_similarity_backend] = lambda: (
        FakeSimilarityBackend(
            [SimilarityMatch(source_id=existing.id, score=0.98)]
        )
    )
    app.dependency_overrides[dependencies.get_embedding_generator] = lambda: (
        TokenHashEmbeddingGenerator(dimension=768)
    )
    payload = _payload(session, confirm_duplicate=True)

    response = client.post(
        "/submissions",
        json=payload,
        headers=_headers(db_session, user),
    )

    assert response.status_code == 201
    created = db_session.get(
        ParliamentaryRecord,
        response.json()["record"]["id"],
    )
    assert created is not None
    assert len(created.embedding) == 768
    assert db_session.query(ParliamentaryRecord).count() == 2
