from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord
from app.similarity.previously_addressed import (
    ADDRESSED_STATUSES,
    PreviouslyAddressedMatch,
)

AUTO_LINK_SIMILARITY_THRESHOLD = 0.85


class RelatedItemLinker(ABC):
    @abstractmethod
    def link(
        self,
        record: ParliamentaryRecord,
        matches: list[PreviouslyAddressedMatch],
    ) -> int:
        """Persist new high-confidence links and return their count."""


class RelatedItemLinkService(RelatedItemLinker):
    """Owns idempotent persistence of directional related-item links."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def link(
        self,
        record: ParliamentaryRecord,
        matches: list[PreviouslyAddressedMatch],
    ) -> int:
        candidate_ids = {
            match.source_id
            for match in matches
            if match.score >= AUTO_LINK_SIMILARITY_THRESHOLD
            and match.source_id != record.id
        }
        if not candidate_ids:
            return 0

        sources = list(
            self._db.scalars(
                select(ParliamentaryRecord)
                .where(ParliamentaryRecord.id.in_(candidate_ids))
                .where(ParliamentaryRecord.status.in_(ADDRESSED_STATUSES))
            ).all()
        )
        existing_ids = {item.id for item in record.related_items}
        added = 0
        for source in sources:
            if source.id in existing_ids:
                continue
            record.related_items.append(source)
            existing_ids.add(source.id)
            added += 1
        return added
