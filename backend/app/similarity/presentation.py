from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import ParliamentaryRecord
from app.similarity.duplicate_detection import DuplicateMatch


@dataclass(frozen=True, slots=True)
class SimilarityDisplayMatch:
    rank: int
    score: float
    match_type: str
    session: str
    date: date
    member_name: str
    source_record: UUID
    source_id: UUID
    ranking_score: float
    cosine_similarity: float | None
    lexical_rank: int | None


class SimilarityResultFormatter(ABC):
    @abstractmethod
    def format(
        self,
        matches: list[DuplicateMatch],
    ) -> list[SimilarityDisplayMatch]:
        """Add source-record context without performing similarity search."""


class DatabaseSimilarityResultFormatter(SimilarityResultFormatter):
    """Shapes domain matches for API display using source record metadata."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def format(
        self,
        matches: list[DuplicateMatch],
    ) -> list[SimilarityDisplayMatch]:
        if not matches:
            return []

        records = {
            record.id: record
            for record in self._db.scalars(
                select(ParliamentaryRecord)
                .options(joinedload(ParliamentaryRecord.session))
                .where(
                    ParliamentaryRecord.id.in_(
                        [match.source_id for match in matches]
                    )
                )
            ).all()
        }
        ordered_matches = sorted(
            matches,
            key=lambda match: (-match.score, str(match.source_id)),
        )

        results = []
        for match in ordered_matches:
            record = records.get(match.source_id)
            if record is None:
                continue
            record_date = (
                record.sitting_date
                if record.sitting_date is not None
                else record.created_at.date()
            )
            results.append(
                SimilarityDisplayMatch(
                    rank=len(results) + 1,
                    score=match.score,
                    match_type=match.match_type,
                    session=record.session.code,
                    date=record_date,
                    member_name=record.member,
                    source_record=record.id,
                    source_id=record.id,
                    ranking_score=(
                        match.ranking_score
                        if match.ranking_score is not None
                        else match.score
                    ),
                    cosine_similarity=match.cosine_similarity,
                    lexical_rank=match.lexical_rank,
                )
            )
        return results
