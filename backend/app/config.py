from functools import lru_cache
from os import getenv

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str
    frontend_origin: str
    ollama_base_url: str
    ollama_embedding_model: str
    ollama_embedding_model_digest: str | None
    ollama_llm_model: str
    ollama_llm_model_digest: str | None
    ai_embedding_dimension: int
    ai_rrf_k: int
    ai_lexical_top_k: int
    ai_semantic_top_k: int
    ai_final_top_k: int
    ai_explanation_enabled: bool
    ai_explanation_max_tokens: int
    ai_explanation_query_max_chars: int
    ai_explanation_evidence_max_chars: int
    ai_explanation_context_max_chars: int
    ai_prompt_version: str
    ai_request_timeout: float
    ai_connect_timeout: float
    ai_max_retries: int
    ai_circuit_break_seconds: float
    ai_chunk_max_chars: int
    ai_chunk_overlap_chars: int
    ai_preprocessing_version: str
    similarity_threshold_version: str
    duplicate_similarity_threshold: float
    automatic_link_similarity_threshold: float
    previously_addressed_threshold: float
    upload_parse_timeout_seconds: float
    upload_parse_memory_mb: int
    upload_temp_directory: str | None
    db_pool_size: int
    db_max_overflow: int
    db_pool_recycle_seconds: int
    db_pool_timeout: float
    db_statement_timeout_ms: int
    log_level: str
    log_json: bool
    worker_stale_seconds: int
    readiness_ai_timeout_seconds: float
    ai_required: bool

    def __init__(self) -> None:
        self.database_url = getenv(
            "DATABASE_URL",
            "postgresql+psycopg://naz_user:naz_password@localhost:5432/naz_order_papers",
        )
        self.frontend_origin = getenv("FRONTEND_ORIGIN", "http://localhost:3000")
        self.ollama_base_url = getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ).rstrip("/")
        self.ollama_embedding_model = getenv(
            "OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m"
        )
        self.ollama_embedding_model_digest = (
            getenv("OLLAMA_EMBEDDING_MODEL_DIGEST", "").strip() or None
        )
        self.ollama_llm_model = getenv("OLLAMA_LLM_MODEL", "qwen3.5:4b")
        self.ollama_llm_model_digest = (
            getenv("OLLAMA_LLM_MODEL_DIGEST", "").strip() or None
        )
        self.ai_embedding_dimension = int(getenv("AI_EMBEDDING_DIMENSION", "768"))
        self.ai_rrf_k = int(getenv("AI_RRF_K", "60"))
        self.ai_lexical_top_k = int(getenv("AI_LEXICAL_TOP_K", "20"))
        self.ai_semantic_top_k = int(getenv("AI_SEMANTIC_TOP_K", "20"))
        self.ai_final_top_k = int(getenv("AI_FINAL_TOP_K", "5"))
        self.ai_explanation_enabled = getenv(
            "AI_EXPLANATION_ENABLED", "true"
        ).strip().casefold() in {"1", "true", "yes", "on"}
        self.ai_explanation_max_tokens = int(
            getenv("AI_EXPLANATION_MAX_TOKENS", "400")
        )
        self.ai_explanation_query_max_chars = int(
            getenv("AI_EXPLANATION_QUERY_MAX_CHARS", "4000")
        )
        self.ai_explanation_evidence_max_chars = int(
            getenv("AI_EXPLANATION_EVIDENCE_MAX_CHARS", "6000")
        )
        self.ai_explanation_context_max_chars = int(
            getenv("AI_EXPLANATION_CONTEXT_MAX_CHARS", "18000")
        )
        self.ai_prompt_version = getenv("AI_PROMPT_VERSION", "grounded-v1").strip()
        self.ai_request_timeout = float(getenv("AI_REQUEST_TIMEOUT", "120"))
        self.ai_connect_timeout = float(getenv("AI_CONNECT_TIMEOUT", "5"))
        self.ai_max_retries = int(getenv("AI_MAX_RETRIES", "2"))
        self.ai_circuit_break_seconds = float(
            getenv("AI_CIRCUIT_BREAK_SECONDS", "30")
        )
        self.ai_chunk_max_chars = int(getenv("AI_CHUNK_MAX_CHARS", "1800"))
        self.ai_chunk_overlap_chars = int(getenv("AI_CHUNK_OVERLAP_CHARS", "240"))
        self.ai_preprocessing_version = getenv(
            "AI_PREPROCESSING_VERSION", "chunks-v1"
        ).strip()
        self.similarity_threshold_version = getenv(
            "SIMILARITY_THRESHOLD_VERSION", "2026-08-05-v1"
        ).strip()
        self.duplicate_similarity_threshold = float(
            getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.95")
        )
        self.automatic_link_similarity_threshold = float(
            getenv("AUTOMATIC_LINK_SIMILARITY_THRESHOLD", "0.99")
        )
        self.previously_addressed_threshold = float(
            getenv("PREVIOUSLY_ADDRESSED_THRESHOLD", "0.72")
        )
        self.upload_parse_timeout_seconds = float(
            getenv("UPLOAD_PARSE_TIMEOUT_SECONDS", "15")
        )
        self.upload_parse_memory_mb = int(
            getenv("UPLOAD_PARSE_MEMORY_MB", "1024")
        )
        self.upload_temp_directory = (
            getenv("UPLOAD_TEMP_DIRECTORY", "").strip() or None
        )
        self.db_pool_size = int(getenv("DB_POOL_SIZE", "10"))
        self.db_max_overflow = int(getenv("DB_MAX_OVERFLOW", "20"))
        self.db_pool_recycle_seconds = int(
            getenv("DB_POOL_RECYCLE_SECONDS", "1800")
        )
        self.db_pool_timeout = float(getenv("DB_POOL_TIMEOUT", "30"))
        self.db_statement_timeout_ms = int(
            getenv("DB_STATEMENT_TIMEOUT_MS", "30000")
        )
        self.log_level = getenv("LOG_LEVEL", "INFO").strip().upper()
        self.log_json = getenv("LOG_JSON", "true").strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.worker_stale_seconds = int(getenv("WORKER_STALE_SECONDS", "30"))
        self.readiness_ai_timeout_seconds = float(
            getenv("READINESS_AI_TIMEOUT_SECONDS", "1")
        )
        self.ai_required = getenv("AI_REQUIRED", "false").strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
