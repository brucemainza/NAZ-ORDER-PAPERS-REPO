from uuid import UUID

from app.ai.interfaces import RankFusion
from app.ai.schemas import RecordMatch
from app.config import Settings


class RRFRankFusion(RankFusion):
    """Reciprocal Rank Fusion.

    Combines multiple ranked lists by summing 1 / (k + rank) for each
    document. Score-scale independent and robust for merging lexical and
    semantic results.
    """

    def __init__(self, settings: Settings) -> None:
        self._k = settings.ai_rrf_k

    def combine(self, *ranked_lists: list[RecordMatch]) -> list[RecordMatch]:
        scores: dict[UUID, float] = {}
        metadata: dict[UUID, dict] = {}
        lexical_rank: dict[UUID, int] = {}
        semantic_rank: dict[UUID, int] = {}
        lexical_scores: dict[UUID, float] = {}
        cosine_similarities: dict[UUID, float] = {}

        for result_list in ranked_lists:
            for match in result_list:
                scores[match.record_id] = scores.get(match.record_id, 0.0)
                if match.lexical_rank is not None:
                    scores[match.record_id] += 1.0 / (self._k + match.lexical_rank)
                    lexical_rank[match.record_id] = match.lexical_rank
                if match.lexical_score is not None:
                    lexical_scores[match.record_id] = match.lexical_score
                if match.semantic_rank is not None:
                    scores[match.record_id] += 1.0 / (self._k + match.semantic_rank)
                    semantic_rank[match.record_id] = match.semantic_rank
                if match.cosine_similarity is not None:
                    cosine_similarities[match.record_id] = match.cosine_similarity
                # Keep the richest metadata we see.
                metadata.setdefault(match.record_id, {}).update(match.metadata or {})

        fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        # Maximum possible RRF score is when a document is ranked #1 in every list.
        max_possible_score = sum(1.0 / (self._k + 1) for _ in ranked_lists)
        return [
            RecordMatch(
                record_id=record_id,
                score=round(score / max(max_possible_score, 1e-9), 6),
                ranking_score=round(
                    score / max(max_possible_score, 1e-9), 6
                ),
                cosine_similarity=cosine_similarities.get(record_id),
                lexical_score=lexical_scores.get(record_id),
                lexical_rank=lexical_rank.get(record_id),
                semantic_rank=semantic_rank.get(record_id),
                rrf_score=round(score, 6),
                metadata=metadata.get(record_id, {}),
            )
            for record_id, score in fused
        ]
