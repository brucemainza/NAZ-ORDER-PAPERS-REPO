from datetime import date, datetime, timedelta, timezone

import pytest

from app.lib.auth import create_access_token
from app.models import (
    ParliamentaryRecord,
    ParliamentarySession,
    Permission,
    Role,
    User,
    UserSession,
)
from app.main import app
from app.similarity.dependencies import (
    get_duplicate_checker,
    get_embedding_generator,
    get_previously_addressed_checker,
)
from app.similarity.duplicate_detection import DuplicateCheckResult
from app.similarity.previously_addressed import PreviouslyAddressedResult


def create_active_session(db_session):
    session = ParliamentarySession(
        code="TEST-QUESTION-SESSION",
        name="Question Test Session",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="Active",
    )
    db_session.add(session)
    db_session.commit()
    return session


def create_user_with_permissions(db_session, *permission_codes):
    permissions = [
        Permission(code=code, description=code.replace("_", " ").title())
        for code in permission_codes
    ]
    role = Role(name=f"Question Role {len(permission_codes)}", permissions=permissions)
    user = User(
        employee_id=f"EMP-QUESTION-{len(permission_codes)}",
        name="Question Submitter",
        role="Viewer",
        status="Active",
        roles=[role],
    )
    db_session.add(user)
    db_session.commit()
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


def question_payload(session_id, answer_type="Oral"):
    return {
        "item_type": "Question",
        "answer_type": answer_type,
        "session_id": str(session_id),
        "member": "Hon. Question Member",
        "ministry": "Ministry of Health",
        "subject": "Rural clinic staffing levels",
        "full_text": (
            "What measures will the Ministry take to improve staffing levels "
            "at rural health clinics during the current parliamentary session?"
        ),
    }


@pytest.mark.parametrize("answer_type", ["Oral", "Written"])
def test_submit_question_with_oral_or_written_answer_type(
    client,
    db_session,
    answer_type,
):
    session = create_active_session(db_session)
    user = create_user_with_permissions(db_session, "submit_question")

    response = client.post(
        "/submissions",
        json=question_payload(session.id, answer_type),
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 201
    assert response.json()["record"]["answer_type"] == answer_type
    record = db_session.get(ParliamentaryRecord, response.json()["record"]["id"])
    assert record.answer_type == answer_type


@pytest.mark.parametrize("answer_type", [None, "Immediate"])
def test_question_rejects_missing_or_invalid_answer_type(
    client,
    db_session,
    answer_type,
):
    session = create_active_session(db_session)
    user = create_user_with_permissions(db_session, "submit_question")
    payload = question_payload(session.id, answer_type)
    if answer_type is None:
        payload.pop("answer_type")

    response = client.post(
        "/submissions",
        json=payload,
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 422


def test_user_without_submit_question_permission_cannot_submit_question(
    client,
    db_session,
):
    session = create_active_session(db_session)
    user = create_user_with_permissions(db_session)

    response = client.post(
        "/submissions",
        json=question_payload(session.id),
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 403
    assert db_session.query(ParliamentaryRecord).count() == 0


class _NoDuplicates:
    def check(self, **_kwargs):
        return DuplicateCheckResult(matches=[])


class _NoPreviouslyAddressed:
    def check(self, **_kwargs):
        return PreviouslyAddressedResult(matches=[])


class _OfflineEmbeddingGenerator:
    model_name = "offline-model"

    def embed(self, _text):
        raise RuntimeError("Ollama is offline")


def test_submission_succeeds_when_embedding_service_is_offline(
    client,
    db_session,
    monkeypatch,
):
    session = create_active_session(db_session)
    user = create_user_with_permissions(db_session, "submit_question")
    app.dependency_overrides[get_duplicate_checker] = lambda: _NoDuplicates()
    app.dependency_overrides[get_previously_addressed_checker] = (
        lambda: _NoPreviouslyAddressed()
    )
    app.dependency_overrides[get_embedding_generator] = (
        lambda: _OfflineEmbeddingGenerator()
    )
    monkeypatch.setattr(
        "app.routers.submissions.find_previously_addressed_candidates",
        lambda *_args, **_kwargs: [],
    )

    response = client.post(
        "/submissions",
        json=question_payload(session.id),
        headers=auth_headers(db_session, user),
    )

    assert response.status_code == 201
    assert response.json()["ai_degraded"] is True
    assert response.json()["warnings"] == [
        "Semantic indexing is queued because the AI service is unavailable."
    ]
    saved = db_session.get(ParliamentaryRecord, response.json()["record"]["id"])
    assert saved.embedding is None
