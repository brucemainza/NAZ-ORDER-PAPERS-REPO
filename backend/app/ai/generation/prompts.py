from uuid import UUID


PARLIAMENTARY_SYSTEM_PROMPT = """You are a procedural verification assistant for the National Assembly of Zambia.
You help authorised parliamentary support staff decide whether a newly submitted question or motion has been asked or moved before.

Rules:
1. Use ONLY the historical records supplied in the Evidence section. Never use outside knowledge.
2. For each record in Evidence, classify its relationship to the draft as one of: exact_duplicate, potential_duplicate, related_matter, or not_related.
3. Cite specific metadata: sitting date, session name, submitting member, ministry, and record ID.
4. Explain shared subject matter AND important differences (time period, district/constituency, ministry, specific request).
5. If no record is meaningfully similar, classify the overall result as no_strong_match.
6. A human reviewer makes the final procedural decision.
7. Return valid JSON matching the requested schema exactly.
"""


EXPLANATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {
            "type": "string",
            "enum": ["exact_duplicate", "potential_duplicate", "related_matter", "no_strong_match"],
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "summary": {"type": "string"},
        "shared_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "important_differences": {
            "type": "array",
            "items": {"type": "string"},
        },
        "supporting_record_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "human_review_required": {"type": "boolean"},
    },
    "required": [
        "classification",
        "confidence",
        "summary",
        "shared_points",
        "important_differences",
        "supporting_record_ids",
        "human_review_required",
    ],
}


def format_evidence(records: list[dict]) -> str:
    lines = []
    for index, record in enumerate(records, start=1):
        record_id = record.get("record_id")
        if isinstance(record_id, UUID):
            record_id = str(record_id)
        lines.append(f"Record {index}:")
        lines.append(f"  ID: {record_id or 'unknown'}")
        lines.append(f"  Session: {record.get('session') or 'unknown'}")
        lines.append(f"  Sitting date: {record.get('sitting_date') or 'unknown'}")
        lines.append(f"  Member: {record.get('member') or 'unknown'}")
        lines.append(f"  Ministry: {record.get('ministry') or 'unknown'}")
        lines.append(f"  Subject: {record.get('subject') or ''}")
        lines.append(f"  Full text: {record.get('full_text') or ''}")
        lines.append("")
    return "\n".join(lines)


def build_explanation_prompt(query_text: str, evidence: list[dict]) -> str:
    evidence_text = format_evidence(evidence) if evidence else "No historical records supplied."
    return f"""Draft submitted for verification:
{query_text}

Evidence (historical records only):
{evidence_text}

Based only on the evidence above, return JSON matching this schema:
{EXPLANATION_JSON_SCHEMA}
"""
