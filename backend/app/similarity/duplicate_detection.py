from abc import ABC, abstractmethod
from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord
from app.similarity.base import SimilarityBackend

DUPLICATE_SIMILARITY_THRESHOLD = 0.95
DEFAULT_DUPLICATE_LIMIT = 5


def normalize_exact_text(text: str) -> str:
    return " ".join(text.casefold().split())


def build_similarity_text(subject: str, full_text: str) -> str:
    return f"{subject.strip()}\n{full_text.strip()}"


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    source_id: UUID
    score: float
    match_type: str


@dataclass(frozen=True, slots=True)
class DuplicateCheckResult:
    matches: list[DuplicateMatch]

    @property
    def is_duplicate(self) -> bool:
        return bool(self.matches)


class DuplicateChecker(ABC):
    @abstractmethod
    def check(
        self,
        *,
        subject: str,
        full_text: str,
        item_type: str,
        exclude_ids: Collection[UUID] = (),
        limit: int = DEFAULT_DUPLICATE_LIMIT,
    ) -> DuplicateCheckResult:
        """Find exact and high-confidence semantic duplicates."""


class DuplicateDetectionService(DuplicateChecker):
    """Coordinates exact lookup with a swappable similarity backend."""

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
        exclude_ids: Collection[UUID] = (),
        limit: int = DEFAULT_DUPLICATE_LIMIT,
    ) -> DuplicateCheckResult:
        normalized_text = normalize_exact_text(full_text)
        excluded = tuple(exclude_ids)
        exact_query = (
            select(ParliamentaryRecord.id)
            .where(ParliamentaryRecord.item_type == item_type)
            .where(ParliamentaryRecord.status != "Draft")
            .where(
                func.regexp_replace(
                    func.lower(ParliamentaryRecord.full_text),
                    r"\s+",
                    " ",
                    "g",
                )
                == normalized_text
            )
            .order_by(ParliamentaryRecord.created_at.desc())
            .limit(limit)
        )
        if excluded:
            exact_query = exact_query.where(
                ParliamentaryRecord.id.not_in(excluded)
            )

        exact_ids = list(self._db.scalars(exact_query).all())
        matches_by_id = {
            source_id: DuplicateMatch(
                source_id=source_id,
                score=1.0,
                match_type="exact",
            )
            for source_id in exact_ids
        }

        semantic_matches = self._similarity_backend.find_similar(
            build_similarity_text(subject, full_text),
            threshold=DUPLICATE_SIMILARITY_THRESHOLD,
            top_n=limit,
            exclude_ids=excluded,
            item_type=item_type,
        )
        for match in semantic_matches:
            matches_by_id.setdefault(
                match.source_id,
                DuplicateMatch(
                    source_id=match.source_id,
                    score=match.score,
                    match_type="semantic",
                ),
            )

        ordered_matches = sorted(
            matches_by_id.values(),
            key=lambda match: (-match.score, str(match.source_id)),
        )[:limit]
        return DuplicateCheckResult(matches=ordered_matches)
