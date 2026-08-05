from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.ai.dependencies import get_ai_service
from app.ai.schemas import (
    AIExplanation,
    RecordMatch,
    SimilaritySearchResponse,
)
from app.lib.auth import create_access_token
from app.main import app
from app.models import (
    AIInferenceRun,
    AuditLog,
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    ReviewDecision,
    Role,
    User,
    UserSession,
)


class FakeAIService:
    def __init__(self, *, supporting_ids=(), human_review_required=False):
        self.supporting_ids = list(supporting_ids)
        self.human_review_required = human_review_required
        self.evidence = None

    def explain(self, query_text, evidence):
        self.evidence = evidence
        return AIExplanation(
            classification="potential_duplicate",
            confidence="high",
            summary="Grounded test explanation",
            supporting_record_ids=self.supporting_ids,
            human_review_required=self.human_review_required,
            model="test-model",
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


def test_ai_explain_requires_review_permission(client, db_session):
    record = _record(db_session)
    viewer = _user(db_session, "EMP-AI-VIEWER")
    fake = FakeAIService()
    app.dependency_overrides[get_ai_service] = lambda: fake

    response = client.post(
        "/ai/explain",
        json={"query_text": "new draft", "record_ids": [str(record.id)]},
        headers=_headers(db_session, viewer),
    )

    assert response.status_code == 403
    assert fake.evidence is None


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


def test_ai_explain_hides_inaccessible_archive(client, db_session):
    record = _record(db_session, status="Archived", code="AI-ARCHIVE")
    reviewer = _user(db_session, "EMP-AI-REVIEWER", "review_submission")
    fake = FakeAIService()
    app.dependency_overrides[get_ai_service] = lambda: fake

    response = client.post(
        "/ai/explain",
        json={"query_text": "new draft", "record_ids": [str(record.id)]},
        headers=_headers(db_session, reviewer),
    )

    assert response.status_code == 404
    assert fake.evidence is None


def test_ai_explain_sanitizes_model_ids_forces_review_and_audits(
    client,
    db_session,
):
    record = _record(db_session, status="Archived", code="AI-AUDIT")
    reviewer = _user(
        db_session,
        "EMP-AI-AUDITOR",
        "review_submission",
        "view_archive",
    )
    fake = FakeAIService(
        supporting_ids=[record.id, uuid4()],
        human_review_required=False,
    )
    app.dependency_overrides[get_ai_service] = lambda: fake

    response = client.post(
        "/ai/explain",
        json={"query_text": "new draft", "record_ids": [str(record.id)]},
        headers=_headers(db_session, reviewer),
    )

    assert response.status_code == 200
    assert response.json()["supporting_record_ids"] == [str(record.id)]
    assert response.json()["human_review_required"] is True
    assert fake.evidence[0]["record_id"] == record.id
    audit = db_session.query(AuditLog).filter_by(action="ai_explanation").one()
    assert audit.user_id == reviewer.id
    assert audit.entity_id == str(record.id)


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


def test_async_explanation_can_be_created_and_polled(client, db_session):
    record = _record(db_session, code="AI-ASYNC")
    reviewer = _user(db_session, "EMP-AI-ASYNC", "review_submission")
    headers = _headers(db_session, reviewer)

    created = client.post(
        "/ai/explanations",
        json={"query_text": "Compare this water question", "record_ids": [str(record.id)]},
        headers=headers,
    )

    assert created.status_code == 202
    run = db_session.get(AIInferenceRun, created.json()["run_id"])
    assert run.outcome == "queued"
    run.outcome = "completed"
    run.result = {
        "classification": "no_strong_match",
        "confidence": "low",
        "summary": "No strong match was found.",
        "shared_points": [],
        "important_differences": [],
        "supporting_record_ids": [],
        "evidence_assessments": [
            {
                "record_id": str(record.id),
                "classification": "not_related",
                "rationale": "The requests concern different programmes.",
            }
        ],
        "human_review_required": True,
        "model": "test-model",
        "error": None,
    }
    db_session.commit()

    polled = client.get(f"/ai/explanations/{run.id}", headers=headers)

    assert polled.status_code == 200
    assert polled.json()["status"] == "completed"
    assert polled.json()["result"]["human_review_required"] is True
