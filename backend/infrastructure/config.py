import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv


def load_environment() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


load_environment()


class Settings:
    app_name: str = "CFO Financial Intelligence API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/cfo_platform"
    database_connect_timeout: int = 3
    allowed_origins: List[str] = ["http://localhost:3000"]

    def __init__(self) -> None:
        self.app_name = os.getenv("CFO_APP_NAME", self.app_name)
        self.api_prefix = os.getenv("CFO_API_PREFIX", self.api_prefix)
        self.environment = os.getenv("CFO_ENVIRONMENT", self.environment)
        self.database_url = os.getenv("CFO_DATABASE_URL", self.database_url)
        self.database_connect_timeout = int(os.getenv("CFO_DATABASE_CONNECT_TIMEOUT", str(self.database_connect_timeout)))
        origins = os.getenv("CFO_ALLOWED_ORIGINS")
        if origins:
            self.allowed_origins = [origin.strip() for origin in origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    load_environment()
    return Settings()
