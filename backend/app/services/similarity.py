from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_embedding_provider
from app.ai.schemas import SimilaritySearchRequest
from app.ai.service import AISimilarityService
from app.config import get_settings
from app.models import ParliamentaryRecord


class CandidateRecord(Protocol):
    @property
    def id(self) -> object: ...


@dataclass
class RankedMatch:
    """Compatibility result used by the submission candidate workflow."""

    record: CandidateRecord
    score: float
    matched_terms: list[str]


def find_previously_addressed_candidates(
    db: Session,
    *,
    record: ParliamentaryRecord,
    user,
    limit: int = 5,
) -> list[RankedMatch]:
    """Find related historical records using hybrid lexical + semantic retrieval.

    PostgreSQL full-text and compatible chunk-vector ranks are fused through
    the AI service while this adapter preserves the existing router contract.
    """
    settings = get_settings()
    embedding_provider = get_embedding_provider()
    service = AISimilarityService(
        db=db,
        user=user,
        settings=settings,
        embedding_provider=embedding_provider,
    )

    query_text = " ".join(
        part
        for part in [
            record.subject,
            record.full_text,
            record.member,
            record.ministry or "",
        ]
        if part
    )

    request = SimilaritySearchRequest(
        query_text=query_text,
        item_type=record.item_type,
        exclude_ids=[record.id],
    )

    response = service.search(request)
    record_ids = [match.record_id for match in response.results[:limit]]
    if not record_ids:
        return []

    records = {
        item.id: item
        for item in db.execute(
            select(ParliamentaryRecord).where(ParliamentaryRecord.id.in_(record_ids))
        ).scalars().all()
    }

    return [
        RankedMatch(
            record=records[match.record_id],
            score=round(match.score * 100, 2),
            matched_terms=match.metadata.get("matched_terms", ["hybrid"]),
        )
        for match in response.results[:limit]
        if match.record_id in records
    ]
