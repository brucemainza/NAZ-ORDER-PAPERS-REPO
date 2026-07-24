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


@lru_cache
def get_settings() -> Settings:
    return Settings()
