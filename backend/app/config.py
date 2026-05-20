from functools import lru_cache
from os import getenv

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str
    frontend_origin: str

    def __init__(self) -> None:
        self.database_url = getenv(
            "DATABASE_URL",
            "postgresql+psycopg://naz_user:naz_password@localhost:5432/naz_order_papers",
        )
        self.frontend_origin = getenv("FRONTEND_ORIGIN", "http://localhost:3000")


@lru_cache
def get_settings() -> Settings:
    return Settings()
