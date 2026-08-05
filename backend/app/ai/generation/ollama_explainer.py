import json
import logging
from typing import Any

import httpx

from app.ai.generation.prompts import (
    EXPLANATION_JSON_SCHEMA,
    PARLIAMENTARY_SYSTEM_PROMPT,
    build_explanation_prompt,
)
from app.ai.interfaces import ExplanationProvider
from app.ai.schemas import AIExplanation
from app.config import Settings

logger = logging.getLogger(__name__)


class OllamaExplanationProvider(ExplanationProvider):
    """Grounded explanation provider backed by a local Ollama chat model."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_llm_model
        self._max_tokens = settings.ai_explanation_max_tokens
        self._timeout = settings.ai_request_timeout

    def explain(self, query_text: str, evidence: list[dict]) -> AIExplanation:
        prompt = build_explanation_prompt(query_text, evidence)
        try:
            raw = self._chat(prompt)
            structured = self._parse_json(raw)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.exception("Ollama explanation request failed")
            return self._fallback(
                "The local explanation model is unavailable. Please review the retrieved records manually.",
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse explanation JSON: %s", exc)
            # Retry once with a stricter reminder.
            try:
                raw = self._chat(
                    prompt + "\n\nIMPORTANT: return ONLY valid JSON, no markdown, no commentary."
                )
                structured = self._parse_json(raw)
            except Exception as retry_exc:
                logger.warning("Explanation retry failed: %s", retry_exc)
                return self._fallback(
                    "The explanation model returned an unparseable response. Please review the retrieved records manually.",
                )

        return self._to_schema(structured)

    def _chat(self, prompt: str) -> str:
        url = f"{self._base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": PARLIAMENTARY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": EXPLANATION_JSON_SCHEMA,
            "options": {
                "temperature": 0.1,
                "num_ctx": 4096,
                "num_predict": self._max_tokens,
            },
        }

        response = httpx.post(url, json=payload, timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        # Some small models wrap JSON in markdown fences.
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        return json.loads(raw)

    def _to_schema(self, data: dict) -> AIExplanation:
        return AIExplanation(
            classification=data.get("classification", "no_strong_match"),
            confidence=data.get("confidence", "low"),
            summary=data.get("summary", ""),
            shared_points=data.get("shared_points", []),
            important_differences=data.get("important_differences", []),
            supporting_record_ids=data.get("supporting_record_ids", []),
            human_review_required=data.get("human_review_required", True),
            model=self._model,
        )

    def _fallback(self, summary: str) -> AIExplanation:
        return AIExplanation(
            classification="no_strong_match",
            confidence="low",
            summary=summary,
            shared_points=[],
            important_differences=[],
            supporting_record_ids=[],
            human_review_required=True,
            model=self._model,
            error=summary,
        )
