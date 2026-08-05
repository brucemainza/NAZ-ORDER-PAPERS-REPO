from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.ai.retrieval.hybrid import RRFRankFusion
from app.ai.schemas import RecordMatch
from app.config import Settings
from app.similarity.evaluation import EvaluationRow, evaluate_thresholds
from app.similarity.normalization import record_content_hash


def test_case_punctuation_and_whitespace_share_an_exact_hash():
    first = record_content_hash(
        "Question",
        "Rural Water—Access!",
        "When   will boreholes be completed?",
    )
    second = record_content_hash(
        " question ",
        "rural water access",
        "WHEN will boreholes be completed",
    )

    assert first == second
    assert len(first) == 64


def test_substantively_different_text_has_a_different_hash():
    baseline = record_content_hash(
        "Question", "Water access", "When will boreholes be completed?"
    )
    changed = record_content_hash(
        "Question", "Water access", "How many boreholes have failed inspection?"
    )

    assert baseline != changed


def test_ranking_score_and_cosine_similarity_are_not_conflated():
    settings = Settings()
    fusion = RRFRankFusion(settings)
    record_id = uuid4()
    lexical = [
        RecordMatch(
            record_id=record_id,
            score=0.21,
            lexical_score=0.21,
            lexical_rank=1,
        )
    ]
    semantic = [
        RecordMatch(
            record_id=record_id,
            score=0.97,
            cosine_similarity=0.97,
            semantic_rank=1,
        )
    ]

    result = fusion.combine(lexical, semantic)[0]

    assert result.score == result.ranking_score
    assert result.cosine_similarity == 0.97
    assert result.lexical_score == 0.21
    assert result.ranking_score != result.cosine_similarity


def test_threshold_evaluation_is_deterministic_and_time_separated():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = [
        EvaluationRow(
            decided_at=start + timedelta(days=index),
            similarity=score,
            is_duplicate=label,
            automatic_link_correct=link,
        )
        for index, (score, label, link) in enumerate(
            [
                (0.20, False, False),
                (0.70, False, False),
                (0.91, True, False),
                (0.97, True, True),
                (0.40, False, False),
                (0.88, False, False),
                (0.94, True, False),
                (0.99, True, True),
            ]
        )
    ]

    first = evaluate_thresholds(rows, split_fraction=0.5)
    second = evaluate_thresholds(list(reversed(rows)), split_fraction=0.5)

    assert first == second
    assert first.training_end < first.validation_start
    assert first.policy_version.startswith("evaluated-")
