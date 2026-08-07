from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://verihire:verihire@localhost:5432/verihire"
    )
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    jwt_secret: SecretStr = SecretStr("dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None

    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: SecretStr | None = None
    s3_bucket: str = "verihire-evidence"

    resend_api_key: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 1025

    sentry_dsn: str | None = None

    safe_browsing_api_key: SecretStr | None = None
    opencorporates_api_key: SecretStr | None = None

    ml_artifacts_dir: str = "../../services/ml/artifacts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
