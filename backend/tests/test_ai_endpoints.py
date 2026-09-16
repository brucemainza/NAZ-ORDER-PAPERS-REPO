from datetime import date, datetime, timedelta, timezone

from app.ai.dependencies import get_ai_service
from app.ai.schemas import RecordMatch, SimilaritySearchResponse
from app.lib.auth import create_access_token
from app.main import app
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    ReviewDecision,
    Role,
    User,
    UserSession,
)


class HealthyHybridSearchService:
    def __init__(self, record_id):
        self.record_id = record_id

    def search(self, _request):
        return SimilaritySearchResponse(
            query_text="water access",
            results=[
                RecordMatch(
                    record_id=self.record_id,
                    score=1.0,
                    lexical_rank=1,
                    semantic_rank=1,
                )
            ],
            embedding_model="embeddinggemma:300m",
            total_lexical=1,
            total_semantic=1,
            retrieval_mode="hybrid",
            degraded=False,
        )


def _user(db_session, employee_id, *permission_codes):
    permissions = [
        Permission(code=code, description=code)
        for code in permission_codes
    ]
    user = User(
        employee_id=employee_id,
        name=employee_id,
        role="Test",
        status="Active",
        roles=[Role(name=f"{employee_id} role", permissions=permissions)],
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


def _record(db_session, *, status="Under Review", code="AI-ENDPOINT"):
    session = ParliamentarySession(
        code=code,
        name=f"{code} session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    record = ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. AI Reviewer",
        ministry="Ministry of Testing",
        answer_type="Written",
        subject="AI evidence record",
        full_text="Historical evidence used to validate the secured AI endpoint.",
        status=status,
    )
    db_session.add(record)
    db_session.commit()
    return record


def test_ai_search_returns_healthy_hybrid_response_shape(client, db_session):
    record = _record(db_session, code="AI-HYBRID")
    user = _user(db_session, "EMP-AI-SEARCH", "view_archive")
    app.dependency_overrides[get_ai_service] = lambda: HealthyHybridSearchService(
        record.id
    )

    response = client.post(
        "/ai/search",
        json={"query_text": "water access"},
        headers=_headers(db_session, user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_mode"] == "hybrid"
    assert payload["degraded"] is False
    assert payload["total_semantic"] == 1
    assert payload["results"][0]["semantic_rank"] == 1


def test_ai_review_uses_established_decision_vocabulary(client, db_session):
    record = _record(db_session, code="AI-REVIEW-RECORD")
    similar = _record(db_session, status="Archived", code="AI-REVIEW-SIMILAR")
    reviewer = _user(db_session, "EMP-AI-DECIDER", "review_submission")

    response = client.post(
        "/ai/review",
        json={
            "record_id": str(record.id),
            "similar_record_id": str(similar.id),
            "decision": "Duplicate",
            "notes": "Confirmed by a human reviewer",
        },
        headers=_headers(db_session, reviewer),
    )

    assert response.status_code == 200
    saved = db_session.get(ReviewDecision, response.json()["review_id"])
    assert saved.decision == "Duplicate"
    assert saved.is_duplicate is True


def test_ai_review_idempotency_replays_one_human_decision(client, db_session):
    record = _record(db_session, code="AI-IDEMPOTENT-RECORD")
    similar = _record(db_session, status="Archived", code="AI-IDEMPOTENT-SIMILAR")
    reviewer = _user(db_session, "EMP-AI-IDEMPOTENT", "review_submission")
    headers = {
        **_headers(db_session, reviewer),
        "Idempotency-Key": "ai-review-001",
    }
    payload = {
        "record_id": str(record.id),
        "similar_record_id": str(similar.id),
        "decision": "Duplicate",
        "notes": "Confirmed once",
    }

    first = client.post("/ai/review", json=payload, headers=headers)
    replay = client.post("/ai/review", json=payload, headers=headers)
    conflict = client.post(
        "/ai/review",
        json={**payload, "notes": "Changed decision payload"},
        headers=headers,
    )

    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert db_session.query(ReviewDecision).count() == 1
