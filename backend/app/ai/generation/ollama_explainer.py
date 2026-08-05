import json
import logging
from typing import Any
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.ai.explanations import prepare_explanation_context
from app.ai.generation.prompts import (
    EXPLANATION_JSON_SCHEMA,
    PARLIAMENTARY_SYSTEM_PROMPT,
    build_explanation_prompt,
)
from app.ai.interfaces import ExplanationProvider
from app.ai.schemas import AIExplanation
from app.config import Settings
from app.observability.metrics import AI_MODEL_CALLS

logger = logging.getLogger(__name__)


class OllamaExplanationProvider(ExplanationProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._model = settings.ollama_llm_model
        self._client = client or httpx.Client(
            base_url=settings.ollama_base_url.rstrip("/"),
            timeout=httpx.Timeout(
                settings.ai_request_timeout,
                connect=settings.ai_connect_timeout,
            ),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    def explain(self, query_text: str, evidence: list[dict]) -> AIExplanation:
        context = prepare_explanation_context(query_text, evidence, self._settings)
        prompt = build_explanation_prompt(
            context.query_text,
            context.serialized_evidence,
        )
        allowed_ids = {UUID(str(item["record_id"])) for item in evidence}
        try:
            return self._validated_explanation(self._chat(prompt), allowed_ids)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("Ollama explanation request failed: %s", exc)
            return self._fallback("The local explanation model is unavailable.")
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            logger.warning("Invalid grounded explanation: %s", exc)
            try:
                reminder = prompt + "\nReturn only valid schema-conforming JSON."
                return self._validated_explanation(self._chat(reminder), allowed_ids)
            except Exception as retry_exc:
                logger.warning("Explanation retry failed: %s", retry_exc)
                return self._fallback(
                    "The explanation was invalid; review the evidence manually."
                )

    def _chat(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": PARLIAMENTARY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "tools": [],
            "think": False,
            "stream": False,
            "format": EXPLANATION_JSON_SCHEMA,
            "options": {
                "temperature": 0.0,
                "num_ctx": 4096,
                "num_predict": self._settings.ai_explanation_max_tokens,
            },
        }
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
        except Exception:
            AI_MODEL_CALLS.labels(
                operation="grounded_explanation",
                outcome="failure",
            ).inc()
            raise
        AI_MODEL_CALLS.labels(
            operation="grounded_explanation",
            outcome="success",
        ).inc()
        return content

    def _validated_explanation(
        self,
        raw: str,
        allowed_ids: set[UUID],
    ) -> AIExplanation:
        data = json.loads(raw.strip())
        data["model"] = self._model
        explanation = AIExplanation.model_validate(data)
        returned_ids = set(explanation.supporting_record_ids) | {
            item.record_id for item in explanation.evidence_assessments
        }
        if not returned_ids.issubset(allowed_ids):
            raise ValueError("model returned an evidence ID that was not supplied")
        return explanation.model_copy(update={"human_review_required": True})

    def _fallback(self, summary: str) -> AIExplanation:
        return AIExplanation(
            classification="no_strong_match",
            confidence="low",
            summary=summary,
            supporting_record_ids=[],
            evidence_assessments=[],
            human_review_required=True,
            model=self._model,
            error=summary,
        )
