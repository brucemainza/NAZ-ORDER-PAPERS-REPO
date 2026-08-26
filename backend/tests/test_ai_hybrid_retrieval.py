from uuid import uuid4

from app.ai.retrieval.hybrid import RRFRankFusion
from app.ai.schemas import RecordMatch
from app.config import Settings


def test_rrf_fusion_prefers_top_ranked_in_both_lists():
    settings = Settings()
    settings.ai_rrf_k = 60
    fusion = RRFRankFusion(settings)

    id_a, id_b, id_c = uuid4(), uuid4(), uuid4()
    lexical = [
        RecordMatch(record_id=id_a, score=1.0, lexical_rank=1),
        RecordMatch(record_id=id_b, score=0.8, lexical_rank=2),
    ]
    semantic = [
        RecordMatch(record_id=id_b, score=0.9, semantic_rank=1),
        RecordMatch(record_id=id_c, score=0.7, semantic_rank=2),
    ]

    result = fusion.combine(lexical, semantic)

    assert len(result) == 3
    # id_b is ranked #1 in semantic and #2 in lexical -> highest combined score.
    assert result[0].record_id == id_b
    assert result[0].lexical_rank == 2
    assert result[0].semantic_rank == 1
    assert result[0].score > 0.0


def test_rrf_fusion_score_is_normalized():
    settings = Settings()
    settings.ai_rrf_k = 60
    fusion = RRFRankFusion(settings)

    record_id = uuid4()
    lexical = [RecordMatch(record_id=record_id, score=1.0, lexical_rank=1)]

    result = fusion.combine(lexical)

    assert len(result) == 1
    assert result[0].score == 1.0


def test_rrf_fusion_with_empty_lists():
    settings = Settings()
    settings.ai_rrf_k = 60
    fusion = RRFRankFusion(settings)

    result = fusion.combine([], [])
    assert result == []
