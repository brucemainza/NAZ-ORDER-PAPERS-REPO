from abc import ABC, abstractmethod
from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SimilarityMatch:
    """A provider-neutral match with a normalized cosine-similarity score."""

    source_id: UUID
    score: float


class SimilarityBackend(ABC):
    """Minimal contract used by duplicate and related-matter services."""

    @abstractmethod
    def find_similar(
        self,
        text: str,
        threshold: float,
        top_n: int,
        *,
        exclude_ids: Collection[UUID] = (),
        statuses: Collection[str] | None = None,
        item_type: str | None = None,
    ) -> list[SimilarityMatch]:
        """Return highest-scoring matches at or above ``threshold``."""

