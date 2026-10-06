from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Local DB credentials
    DB_TYPE: str = "postgresql"  # postgresql, mysql, sqlite
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"

    # Cloud coordination settings
    CLOUD_PLATFORM_URL: str = "http://localhost:8000"
    AGENT_UUID: str = "00000000-0000-0000-0000-000000000000"
    POLL_INTERVAL_SECONDS: int = 5

    # Security & Privacy settings
    PII_MASKING_ENABLED: bool = True
    ENCRYPTION_KEY: Optional[str] = None

settings = Settings()
