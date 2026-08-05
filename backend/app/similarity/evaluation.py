from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class EvaluationRow:
    decided_at: datetime
    similarity: float
    is_duplicate: bool
    automatic_link_correct: bool


@dataclass(frozen=True, slots=True)
class ThresholdEvaluation:
    policy_version: str
    training_end: datetime
    validation_start: datetime
    duplicate_threshold: float
    duplicate_precision: float
    automatic_link_threshold: float
    automatic_link_precision: float


def _precision(rows: list[EvaluationRow], threshold: float, label: str) -> float:
    predicted = [row for row in rows if row.similarity >= threshold]
    if not predicted:
        return 0.0
    correct = sum(bool(getattr(row, label)) for row in predicted)
    return correct / len(predicted)


def _derive_threshold(
    rows: list[EvaluationRow],
    *,
    label: str,
    target_precision: float,
) -> float:
    candidates = sorted({row.similarity for row in rows})
    qualifying = [
        threshold
        for threshold in candidates
        if _precision(rows, threshold, label) >= target_precision
    ]
    if not qualifying:
        return 1.0
    return min(qualifying)


def evaluate_thresholds(
    rows: list[EvaluationRow],
    *,
    split_fraction: float = 0.8,
    duplicate_precision_target: float = 0.95,
    automatic_link_precision_target: float = 0.98,
) -> ThresholdEvaluation:
    if len(rows) < 4:
        raise ValueError("at least four historical decisions are required")
    if not 0.5 <= split_fraction < 1:
        raise ValueError("split_fraction must be between 0.5 and 1")
    ordered = sorted(rows, key=lambda row: (row.decided_at, row.similarity))
    split = max(2, min(len(ordered) - 1, int(len(ordered) * split_fraction)))
    training = ordered[:split]
    validation = ordered[split:]
    duplicate_threshold = _derive_threshold(
        training,
        label="is_duplicate",
        target_precision=duplicate_precision_target,
    )
    link_threshold = _derive_threshold(
        training,
        label="automatic_link_correct",
        target_precision=automatic_link_precision_target,
    )
    identity = "|".join(
        f"{row.decided_at.isoformat()}:{row.similarity:.8f}:"
        f"{int(row.is_duplicate)}:{int(row.automatic_link_correct)}"
        for row in ordered
    )
    version = f"evaluated-{sha256(identity.encode()).hexdigest()[:12]}"
    return ThresholdEvaluation(
        policy_version=version,
        training_end=training[-1].decided_at,
        validation_start=validation[0].decided_at,
        duplicate_threshold=duplicate_threshold,
        duplicate_precision=round(
            _precision(validation, duplicate_threshold, "is_duplicate"), 6
        ),
        automatic_link_threshold=link_threshold,
        automatic_link_precision=round(
            _precision(validation, link_threshold, "automatic_link_correct"), 6
        ),
    )
