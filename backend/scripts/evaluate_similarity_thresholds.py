"""Derive and validate versioned thresholds from historical clerk decisions."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from app.similarity.evaluation import EvaluationRow, evaluate_thresholds


def load_rows(path: Path) -> list[EvaluationRow]:
    with path.open(newline="", encoding="utf-8") as source:
        return [
            EvaluationRow(
                decided_at=datetime.fromisoformat(row["decided_at"]),
                similarity=float(row["cosine_similarity"]),
                is_duplicate=row["is_duplicate"].strip().casefold()
                in {"1", "true", "yes"},
                automatic_link_correct=row["automatic_link_correct"]
                .strip()
                .casefold()
                in {"1", "true", "yes"},
            )
            for row in csv.DictReader(source)
        ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate duplicate and automatic-link thresholds"
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--split-fraction", type=float, default=0.8)
    args = parser.parse_args()
    result = evaluate_thresholds(
        load_rows(args.csv_path),
        split_fraction=args.split_fraction,
    )
    output = {
        "policy_version": result.policy_version,
        "training_end": result.training_end.isoformat(),
        "validation_start": result.validation_start.isoformat(),
        "duplicate_threshold": result.duplicate_threshold,
        "duplicate_precision": result.duplicate_precision,
        "automatic_link_threshold": result.automatic_link_threshold,
        "automatic_link_precision": result.automatic_link_precision,
        "duplicate_precision_target_met": result.duplicate_precision >= 0.95,
        "automatic_link_precision_target_met": (
            result.automatic_link_precision >= 0.98
        ),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if not (
        output["duplicate_precision_target_met"]
        and output["automatic_link_precision_target_met"]
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
