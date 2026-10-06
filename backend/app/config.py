import json
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "nexus-ai"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    APP_SECRET_KEY: str
    
    # DB
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str
    
    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str
    
    # LLM
    OPENROUTER_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gpt-oss:20b"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_NUM_CTX: int = 16384
    OLLAMA_KEEP_ALIVE: str = "2h"
    
    OLLAMA_SECONDARY_BASE_URL: Optional[str] = None
    OLLAMA_SECONDARY_MODEL: Optional[str] = None
    
    LLM_ROUTER_STRATEGY: str = "local_only"
    
    # Limits
    MAX_QUERY_ROWS: int = 10000
    MAX_QUERY_TIMEOUT_SECONDS: int = 30
    BLOCK_WRITE_QUERIES: bool = True
    
    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000"]'
    
    # Notifications — SMTP email alerts
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "alerts@nexus-ai.com"
    ALERT_RECIPIENT_EMAIL: Optional[str] = None
    
    # Notifications — Slack
    SLACK_WEBHOOK_URL: Optional[str] = None

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except json.JSONDecodeError:
            return ["http://localhost:3000"]

settings = Settings()
