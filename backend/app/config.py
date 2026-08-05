from functools import lru_cache
from os import getenv

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str
    frontend_origin: str
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_sender: str
    smtp_use_tls: bool
    smtp_timeout: float

    # AI / local Ollama settings
    ollama_base_url: str
    ollama_embedding_model: str
    ollama_embedding_model_digest: str | None
    ollama_llm_model: str
    ai_embedding_dimension: int
    ai_rrf_k: int
    ai_lexical_top_k: int
    ai_semantic_top_k: int
    ai_final_top_k: int
    ai_explanation_enabled: bool
    ai_explanation_max_tokens: int
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

    def __init__(self) -> None:
        self.database_url = getenv(
            "DATABASE_URL",
            "postgresql+psycopg://naz_user:naz_password@localhost:5432/naz_order_papers",
        )
        self.frontend_origin = getenv("FRONTEND_ORIGIN", "http://localhost:3000")
        self.email_provider = getenv("EMAIL_PROVIDER", "smtp").strip().casefold()
        self.smtp_host = getenv("SMTP_HOST", "localhost").strip()
        self.smtp_port = int(getenv("SMTP_PORT", "25"))
        self.smtp_username = getenv("SMTP_USERNAME") or None
        self.smtp_password = getenv("SMTP_PASSWORD") or None
        self.smtp_sender = getenv(
            "SMTP_SENDER",
            "notifications@localhost",
        ).strip()
        self.smtp_use_tls = getenv("SMTP_USE_TLS", "false").strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.smtp_timeout = float(getenv("SMTP_TIMEOUT", "30"))

        self.ollama_base_url = getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_embedding_model = getenv(
            "OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m"
        )
        self.ollama_embedding_model_digest = (
            getenv("OLLAMA_EMBEDDING_MODEL_DIGEST", "").strip() or None
        )
        self.ollama_llm_model = getenv("OLLAMA_LLM_MODEL", "qwen3.5:4b")
        self.ai_embedding_dimension = int(getenv("AI_EMBEDDING_DIMENSION", "768"))
        self.ai_rrf_k = int(getenv("AI_RRF_K", "60"))
        self.ai_lexical_top_k = int(getenv("AI_LEXICAL_TOP_K", "20"))
        self.ai_semantic_top_k = int(getenv("AI_SEMANTIC_TOP_K", "20"))
        self.ai_final_top_k = int(getenv("AI_FINAL_TOP_K", "5"))
        self.ai_explanation_enabled = getenv(
            "AI_EXPLANATION_ENABLED", "true"
        ).strip().casefold() in {"1", "true", "yes", "on"}
        self.ai_explanation_max_tokens = int(getenv("AI_EXPLANATION_MAX_TOKENS", "400"))
        self.ai_request_timeout = float(getenv("AI_REQUEST_TIMEOUT", "120"))
        self.ai_connect_timeout = float(getenv("AI_CONNECT_TIMEOUT", "5"))
        self.ai_max_retries = int(getenv("AI_MAX_RETRIES", "2"))
        self.ai_circuit_break_seconds = float(
            getenv("AI_CIRCUIT_BREAK_SECONDS", "30")
        )
        self.ai_chunk_max_chars = int(getenv("AI_CHUNK_MAX_CHARS", "1800"))
        self.ai_chunk_overlap_chars = int(
            getenv("AI_CHUNK_OVERLAP_CHARS", "240")
        )
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
