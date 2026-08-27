import importlib
import importlib.util
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

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
from app.similarity.previously_addressed import PreviouslyAddressedMatch


def _load_related_items_module():
    qualified_name = "app.similarity.related_items"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-017 related-item link service has not been implemented"
    )
    return importlib.import_module(qualified_name)


def _session(code, year, *, status=None):
    return ParliamentarySession(
        code=f"{code}-{uuid4()}",
        name=f"{code} Session",
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
        status=status or ("Closed" if year < 2026 else "Active"),
    )


def _record(session, *, status, subject):
    return ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Related Item Member",
        ministry="Water Development",
        answer_type="Oral",
        subject=subject,
        full_text=f"{subject} with enough fixture content for related-item tests.",
        status=status,
    )


def test_high_confidence_link_is_queryable_from_both_sides(db_session):
    related_items = _load_related_items_module()
    old_session = _session("RELATED-OLD", 2025)
    current_session = _session("RELATED-CURRENT", 2026)
    past = _record(
        old_session,
        status="Answered",
        subject="Past rural borehole matter",
    )
    new = _record(
        current_session,
        status="Under Review",
        subject="New rural borehole matter",
    )
    db_session.add_all([past, new])
    db_session.commit()
    linker = related_items.RelatedItemLinkService(db_session)

    linked_count = linker.link(
        new,
        [PreviouslyAddressedMatch(source_id=past.id, score=0.995)],
    )
    db_session.commit()
    db_session.expire_all()

    persisted_new = db_session.get(ParliamentaryRecord, new.id)
    persisted_past = db_session.get(ParliamentaryRecord, past.id)
    assert linked_count == 1
    assert [record.id for record in persisted_new.related_items] == [past.id]
    assert [record.id for record in persisted_past.referenced_by_items] == [
        new.id
    ]


def test_repeated_link_checks_do_not_create_duplicate_rows(db_session):
    related_items = _load_related_items_module()
    models = importlib.import_module("app.models")
    old_session = _session("REPEAT-OLD", 2025)
    current_session = _session("REPEAT-CURRENT", 2026)
    past = _record(old_session, status="Answered", subject="Past linked matter")
    new = _record(
        current_session,
        status="Under Review",
        subject="New linked matter",
    )
    db_session.add_all([past, new])
    db_session.commit()
    linker = related_items.RelatedItemLinkService(db_session)
    matches = [PreviouslyAddressedMatch(source_id=past.id, score=0.995)]

    assert linker.link(new, matches) == 1
    db_session.flush()
    assert linker.link(new, matches) == 0
    db_session.flush()

    row_count = db_session.scalar(
        select(func.count()).select_from(models.related_item_links)
    )
    assert row_count == 1


def test_lower_confidence_related_matter_is_not_automatically_linked(db_session):
    related_items = _load_related_items_module()
    old_session = _session("LOW-OLD", 2025)
    current_session = _session("LOW-CURRENT", 2026)
    past = _record(old_session, status="Discussed", subject="Past low match")
    new = _record(
        current_session,
        status="Under Review",
        subject="New low match",
    )
    db_session.add_all([past, new])
    db_session.commit()

    linked_count = related_items.RelatedItemLinkService(db_session).link(
        new,
        [PreviouslyAddressedMatch(source_id=past.id, score=0.84)],
    )

    assert linked_count == 0
    assert new.related_items == []


class ThresholdAwareFakeBackend(SimilarityBackend):
    def __init__(self, match):
        self.match = match

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
        return [self.match] if self.match.score >= threshold else []


def _user(db_session):
    permission = Permission(
        code="submit_question",
        description="Submit questions",
    )
    user = User(
        employee_id=f"EMP-LINK-{uuid4()}",
        name="Related Item Submitter",
        role="Member",
        status="Active",
        roles=[Role(name=f"Link Role {uuid4()}", permissions=[permission])],
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


def test_accepted_submission_auto_links_high_confidence_addressed_match(
    client,
    db_session,
):
    _load_related_items_module()
    dependencies = importlib.import_module("app.similarity.dependencies")
    old_session = _session("CREATE-LINK-OLD", 2025)
    current_session = _session("CREATE-LINK-CURRENT", 2026)
    past = _record(
        old_session,
        status="Answered",
        subject="Past rural borehole construction",
    )
    user = _user(db_session)
    db_session.add_all([past, current_session])
    db_session.commit()
    app.dependency_overrides[dependencies.get_similarity_backend] = lambda: (
        ThresholdAwareFakeBackend(SimilarityMatch(past.id, 0.995))
    )

    response = client.post(
        "/submissions",
        json={
            "item_type": "Question",
            "session_id": str(current_session.id),
            "member": "Hon. Related Item Submitter",
            "ministry": "Water Development",
            "answer_type": "Oral",
            "subject": "Current rural borehole construction",
            "full_text": (
                "What progress has been made on current rural borehole "
                "construction during this implementation period?"
            ),
            "confirm_duplicate": True,
        },
        headers=_headers(db_session, user),
    )

    assert response.status_code == 201
    created = db_session.get(
        ParliamentaryRecord,
        response.json()["record"]["id"],
    )
    db_session.refresh(created)
    assert [record.id for record in created.related_items] == [past.id]
