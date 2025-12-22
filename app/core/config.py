from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "chat-backend"
    environment: str = Field(default="development")
    debug: bool = False

    database_url: str = Field(default="postgresql+psycopg://chat:chat@localhost:5432/chat")

    llm_provider: str = Field(default="mock")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_temperature: float = 0.2
    llm_max_tokens: int = 400
    openai_api_key: Optional[str] = None

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    log_level: str = Field(default="INFO")
    log_requests: bool = Field(default=False, description="Avoid logging full user content by default")

    # Retrieval and session configuration
    history_window: int = 6
    max_documents: int = 20

    # Rate limiting stub
    rate_limit_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
