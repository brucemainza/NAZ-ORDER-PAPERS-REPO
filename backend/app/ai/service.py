import logging

from sqlalchemy.orm import Session

from app.ai.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.ai.interfaces import EmbeddingProvider, ExplanationProvider, RankFusion
from app.ai.retrieval.hybrid import RRFRankFusion
from app.ai.retrieval.lexical import PostgresLexicalRetriever
from app.ai.retrieval.semantic import PgVectorSemanticRetriever
from app.ai.schemas import (
    AIExplanation,
    AIHealthResponse,
    RecordMatch,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from app.config import Settings

logger = logging.getLogger(__name__)


class AISimilarityService:
    """High-level orchestrator for hybrid similarity search.

    Pipeline:
      1. Validate input.
      2. Optional exact-text check.
      3. Lexical retrieval (BM25 on SQL-filtered candidates).
      4. Semantic retrieval (pgvector cosine distance).
      5. Reciprocal Rank Fusion.
      6. Optional LLM explanation (added by caller if needed).
    """

    def __init__(
        self,
        db: Session,
        user,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
        rank_fusion: RankFusion | None = None,
    ) -> None:
        self._db = db
        self._user = user
        self._settings = settings
        self._embedding_provider = embedding_provider
        self._rank_fusion = rank_fusion or RRFRankFusion(settings)

    def search(
        self,
        request: SimilaritySearchRequest,
        include_explanation: bool = False,
    ) -> SimilaritySearchResponse:
        if not request.query_text.strip():
            return self._empty_response(request)

        requested_limit = request.limit or self._settings.ai_final_top_k
        retrieval_window = request.offset + requested_limit

        # Lexical retrieval.
        lexical = PostgresLexicalRetriever(self._db, self._user)
        lexical_matches = lexical.search(
            request,
            max(self._settings.ai_lexical_top_k, retrieval_window),
        )

        # Semantic retrieval.
        semantic_matches: list[RecordMatch] = []
        retrieval_mode = "hybrid"
        degraded = False
        warnings: list[str] = []
        try:
            query_embedding = self._embedding_provider.embed_query(request.query_text)
            model_digest = getattr(
                self._embedding_provider,
                "model_digest",
                self._embedding_provider.model_name,
            )
            semantic = PgVectorSemanticRetriever(
                self._db,
                self._user,
                model=self._embedding_provider.model_name,
                model_digest=model_digest,
                dimension=self._embedding_provider.dimension,
                preprocessing_version=self._settings.ai_preprocessing_version,
            )
            semantic_matches = semantic.search(
                request,
                query_embedding,
                max(self._settings.ai_semantic_top_k, retrieval_window),
            )
        except RuntimeError as exc:
            logger.warning("Semantic retrieval unavailable; using lexical only: %s", exc)
            retrieval_mode = "lexical"
            degraded = True
            warnings.append("Semantic retrieval is temporarily unavailable.")

        # Fuse and truncate.
        ranked_lists = [lexical_matches]
        if not degraded:
            ranked_lists.append(semantic_matches)
        fused = self._rank_fusion.combine(*ranked_lists)
        final = fused[request.offset : request.offset + requested_limit]

        return SimilaritySearchResponse(
            query_text=request.query_text,
            results=final,
            embedding_model=self._embedding_provider.model_name,
            total_lexical=len(lexical_matches),
            total_semantic=len(semantic_matches),
            retrieval_mode=retrieval_mode,
            degraded=degraded,
            warnings=warnings,
        )

    def explain(self, query_text: str, evidence: list[dict]) -> AIExplanation:
        if not self._settings.ai_explanation_enabled:
            return AIExplanation(
                classification="no_strong_match",
                confidence="low",
                summary="AI explanations are disabled.",
                model=self._settings.ollama_llm_model,
                human_review_required=True,
            )

        explainer = self._get_explainer()
        return explainer.explain(query_text, evidence)

    def health(self) -> AIHealthResponse:
        import httpx

        ollama_reachable = False
        embedding_loaded = False
        llm_loaded = False
        try:
            response = httpx.get(
                f"{self._settings.ollama_base_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
            ollama_reachable = True
            models = {m.get("name") for m in response.json().get("models", [])}
            embedding_loaded = self._settings.ollama_embedding_model in models
            llm_loaded = self._settings.ollama_llm_model in models
        except Exception as exc:
            logger.debug("Ollama health check failed: %s", exc)

        return AIHealthResponse(
            ollama_reachable=ollama_reachable,
            embedding_model_loaded=embedding_loaded,
            llm_model_loaded=llm_loaded,
            embedding_dimension=self._settings.ai_embedding_dimension,
            embedding_model=self._settings.ollama_embedding_model,
            llm_model=self._settings.ollama_llm_model,
        )

    def _empty_response(self, request: SimilaritySearchRequest) -> SimilaritySearchResponse:
        return SimilaritySearchResponse(
            query_text=request.query_text,
            results=[],
            embedding_model=self._embedding_provider.model_name,
            total_lexical=0,
            total_semantic=0,
        )

    def _get_explainer(self) -> ExplanationProvider:
        from app.ai.generation.ollama_explainer import OllamaExplanationProvider

        return OllamaExplanationProvider(self._settings)
