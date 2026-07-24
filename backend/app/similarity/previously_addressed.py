from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import ParliamentaryRecord, ParliamentarySession
from app.similarity.base import SimilarityBackend
from app.similarity.duplicate_detection import build_similarity_text

PREVIOUSLY_ADDRESSED_THRESHOLD = 0.72
ADDRESSED_STATUSES = ("Answered", "Discussed")
DEFAULT_PREVIOUSLY_ADDRESSED_LIMIT = 5
SEARCH_OVERSAMPLE_FACTOR = 3


@dataclass(frozen=True, slots=True)
class PreviouslyAddressedMatch:
    source_id: UUID
    score: float


@dataclass(frozen=True, slots=True)
class PreviouslyAddressedResult:
    matches: list[PreviouslyAddressedMatch]

    @property
    def has_matches(self) -> bool:
        return bool(self.matches)


class PreviouslyAddressedChecker(ABC):
    @abstractmethod
    def check(
        self,
        *,
        subject: str,
        full_text: str,
        item_type: str,
        current_session_id: UUID,
        limit: int = DEFAULT_PREVIOUSLY_ADDRESSED_LIMIT,
    ) -> PreviouslyAddressedResult:
        """Find related addressed matters in genuinely earlier sessions."""


class PreviouslyAddressedService(PreviouslyAddressedChecker):
    def __init__(
        self,
        db: Session,
        similarity_backend: SimilarityBackend,
    ) -> None:
        self._db = db
        self._similarity_backend = similarity_backend

    def check(
        self,
        *,
        subject: str,
        full_text: str,
        item_type: str,
        current_session_id: UUID,
        limit: int = DEFAULT_PREVIOUSLY_ADDRESSED_LIMIT,
    ) -> PreviouslyAddressedResult:
        current_session = self._db.get(
            ParliamentarySession,
            current_session_id,
        )
        if current_session is None:
            return PreviouslyAddressedResult(matches=[])

        backend_matches = self._similarity_backend.find_similar(
            build_similarity_text(subject, full_text),
            threshold=PREVIOUSLY_ADDRESSED_THRESHOLD,
            top_n=limit * SEARCH_OVERSAMPLE_FACTOR,
            statuses=ADDRESSED_STATUSES,
            item_type=item_type,
        )
        if not backend_matches:
            return PreviouslyAddressedResult(matches=[])

        records = {
            record.id: record
            for record in self._db.scalars(
                select(ParliamentaryRecord)
                .options(joinedload(ParliamentaryRecord.session))
                .where(
                    ParliamentaryRecord.id.in_(
                        [match.source_id for match in backend_matches]
                    )
                )
            ).all()
        }
        matches = []
        for match in backend_matches:
            record = records.get(match.source_id)
            if (
                record is None
                or record.status not in ADDRESSED_STATUSES
                or record.item_type != item_type
                or record.session.start_date >= current_session.start_date
            ):
                continue
            matches.append(
                PreviouslyAddressedMatch(
                    source_id=record.id,
                    score=match.score,
                )
            )

        matches.sort(key=lambda match: (-match.score, str(match.source_id)))
        return PreviouslyAddressedResult(matches=matches[:limit])
