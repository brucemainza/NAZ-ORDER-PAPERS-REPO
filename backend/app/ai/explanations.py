import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.normalization import normalize_text
from app.ai.schemas import AIExplanation
from app.config import Settings
from app.jobs.queue import enqueue_outbox_job
from app.models import AIInferenceRun, ParliamentaryRecord, User
from app.services.record_visibility import can_view_record


@dataclass(frozen=True)
class PreparedExplanationContext:
    query_text: str
    serialized_evidence: str
    truncated: bool


def prepare_explanation_context(
    query_text: str,
    evidence: list[dict],
    settings: Settings,
) -> PreparedExplanationContext:
    bounded_query = query_text[: settings.ai_explanation_query_max_chars]
    truncated = bounded_query != query_text
    evidence_budget = max(
        2,
        settings.ai_explanation_context_max_chars - len(bounded_query),
    )
    bounded_records: list[dict] = []
    for source in evidence:
        record = {
            "record_id": str(source.get("record_id", "")),
            "session": str(source.get("session") or ""),
            "sitting_date": str(source.get("sitting_date") or ""),
            "member": str(source.get("member") or ""),
            "ministry": str(source.get("ministry") or ""),
            "subject": str(source.get("subject") or ""),
            "full_text": str(source.get("full_text") or ""),
        }
        if len(record["full_text"]) > settings.ai_explanation_evidence_max_chars:
            record["full_text"] = record["full_text"][
                : settings.ai_explanation_evidence_max_chars
            ]
            truncated = True
        candidate = bounded_records + [record]
        serialized = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
        if len(serialized) > evidence_budget:
            excess = len(serialized) - evidence_budget
            if len(record["full_text"]) > excess:
                record["full_text"] = record["full_text"][: -excess]
                candidate = bounded_records + [record]
                serialized = json.dumps(
                    candidate, ensure_ascii=False, separators=(",", ":")
                )
            if len(serialized) > evidence_budget:
                truncated = True
                break
            truncated = True
        bounded_records.append(record)
    serialized_evidence = json.dumps(
        bounded_records,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return PreparedExplanationContext(
        query_text=bounded_query,
        serialized_evidence=serialized_evidence,
        truncated=truncated,
    )


def inference_cache_key(
    *,
    query_text: str,
    evidence_ids: list[UUID],
    prompt_version: str,
    model_digest: str,
) -> tuple[str, str]:
    query_hash = sha256(normalize_text(query_text).encode("utf-8")).hexdigest()
    identity = "|".join(
        [
            query_hash,
            ",".join(sorted(str(record_id) for record_id in evidence_ids)),
            prompt_version,
            model_digest,
        ]
    )
    return query_hash, sha256(identity.encode("utf-8")).hexdigest()


def queue_explanation(
    db: Session,
    *,
    user: User,
    query_text: str,
    records: list[ParliamentaryRecord],
    settings: Settings,
) -> tuple[AIInferenceRun, bool]:
    evidence_ids = [record.id for record in records]
    model_digest = settings.ollama_llm_model_digest or (
        f"unresolved:{settings.ollama_llm_model}"
    )
    query_hash, cache_key = inference_cache_key(
        query_text=query_text,
        evidence_ids=evidence_ids,
        prompt_version=settings.ai_prompt_version,
        model_digest=model_digest,
    )
    existing = db.scalar(
        select(AIInferenceRun).where(AIInferenceRun.cache_key == cache_key)
    )
    if existing is not None:
        return existing, existing.outcome == "completed"

    context = prepare_explanation_context(
        query_text,
        [
            {
                "record_id": record.id,
                "subject": record.subject,
                "full_text": record.full_text,
                "member": record.member,
                "ministry": record.ministry,
                "session": record.session.name if record.session else None,
                "sitting_date": (
                    record.sitting_date.isoformat() if record.sitting_date else None
                ),
            }
            for record in records
        ],
        settings,
    )
    run = AIInferenceRun(
        run_type="grounded_explanation",
        user_id=user.id,
        query_hash=query_hash,
        evidence_ids=evidence_ids,
        prompt_version=settings.ai_prompt_version,
        model=settings.ollama_llm_model,
        model_digest=model_digest,
        request_metadata={
            "query_text": context.query_text,
            "truncated": context.truncated,
        },
        outcome="queued",
        cache_key=cache_key,
    )
    db.add(run)
    db.flush()
    enqueue_outbox_job(
        db,
        job_type="generate_explanation",
        payload={"run_id": str(run.id)},
        deduplication_key=f"generate_explanation:{cache_key}",
        aggregate_type="ai_inference_run",
        aggregate_id=str(run.id),
        event_type="ai.explanation_requested",
    )
    return run, False


def process_explanation_run(
    db: Session,
    run: AIInferenceRun,
    *,
    provider,
) -> AIExplanation:
    records = {
        record.id: record
        for record in db.scalars(
            select(ParliamentaryRecord).where(
                ParliamentaryRecord.id.in_(run.evidence_ids or [])
            )
        ).all()
    }
    user = db.get(User, run.user_id) if run.user_id else None
    if user is None or len(records) != len(set(run.evidence_ids or [])):
        raise RuntimeError("explanation evidence is no longer available")
    ordered = [records[record_id] for record_id in run.evidence_ids or [] if record_id in records]
    if any(not can_view_record(record, user) for record in ordered):
        raise RuntimeError("explanation evidence is no longer visible")
    query_text = (run.request_metadata or {}).get("query_text", "")
    evidence = [
        {
            "record_id": record.id,
            "subject": record.subject,
            "full_text": record.full_text,
            "member": record.member,
            "ministry": record.ministry,
            "session": record.session.name if record.session else None,
            "sitting_date": record.sitting_date.isoformat() if record.sitting_date else None,
        }
        for record in ordered
    ]
    run.outcome = "running"
    started = perf_counter()
    explanation = provider.explain(query_text, evidence)
    run.latency_ms = round((perf_counter() - started) * 1000)
    run.result = explanation.model_dump(mode="json")
    run.outcome = "failed" if explanation.error else "completed"
    run.error = explanation.error
    run.completed_at = datetime.now(timezone.utc)
    return explanation
