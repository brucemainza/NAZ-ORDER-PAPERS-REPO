import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol


class SearchableRecord(Protocol):
    subject: str
    full_text: str
    member: str
    ministry: str | None


@dataclass
class RankedMatch:
    record: SearchableRecord
    score: float
    matched_terms: list[str]


def tokenize(value: str) -> list[str]:
    return [
        token
        for token in re.sub(r"[^a-z0-9\s]", " ", value.lower()).split()
        if len(token) > 2
    ]


def record_text(record: SearchableRecord) -> str:
    return " ".join(
        part
        for part in [
            record.subject,
            record.full_text,
            record.member,
            record.ministry,
        ]
        if part
    )


def rank_records(
    query_text: str,
    records: list[SearchableRecord],
    limit: int,
) -> list[RankedMatch]:
    query_terms = tokenize(query_text)

    if not query_terms or not records:
        return []

    document_terms = [tokenize(record_text(record)) for record in records]
    document_count = len(document_terms)
    average_document_length = sum(len(document) for document in document_terms) / document_count

    document_frequency: Counter[str] = Counter()
    for document in document_terms:
        document_frequency.update(set(document))

    k1 = 1.5
    b = 0.75
    scored_matches: list[RankedMatch] = []

    for record, document in zip(records, document_terms, strict=True):
        term_frequency = Counter(document)
        document_length = len(document) or 1
        raw_score = 0.0
        matched_terms: list[str] = []

        for term in set(query_terms):
            frequency = term_frequency.get(term, 0)
            if frequency == 0:
                continue

            matched_terms.append(term)
            idf = math.log(1 + (document_count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + k1 * (1 - b + b * document_length / average_document_length)
            raw_score += idf * ((frequency * (k1 + 1)) / denominator)

        if raw_score > 0:
            scored_matches.append(
                RankedMatch(
                    record=record,
                    score=raw_score,
                    matched_terms=sorted(matched_terms),
                )
            )

    scored_matches.sort(key=lambda match: match.score, reverse=True)
    top_matches = scored_matches[:limit]

    if not top_matches:
        return []

    max_score = top_matches[0].score
    return [
        RankedMatch(
            record=match.record,
            score=round((match.score / max_score) * 100, 2),
            matched_terms=match.matched_terms,
        )
        for match in top_matches
    ]
