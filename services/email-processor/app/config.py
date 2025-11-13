"""Application configuration using Pydantic settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/listfig"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "email-processing"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"  # Cost-effective model for summarization

    # API Security
    api_key: str = "dev-secret-key"

    # Email Domains
    email_domains: str = "emails.listfig.com"

    # Logging
    log_level: str = "INFO"

    # Application
    app_name: str = "Listfig Email Processor"
    app_version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def domains_list(self) -> List[str]:
        """Parse comma-separated domains into a list"""
        return [d.strip() for d in self.email_domains.split(",") if d.strip()]


# Global settings instance
settings = Settings()
