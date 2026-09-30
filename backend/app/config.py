from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Normalize provider URLs to SQLAlchemy-friendly form."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Leader Feedback, Poll & Grade System"
    secret_key: str = "change-me-in-production-leader-feedback-secret-key-2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = "sqlite:///./leader_feedback.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    openai_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@leaderfeedback.local"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_discovery_url: str = ""
    frontend_url: str = "http://localhost:3000"
    default_locale: str = "en"
    seed_on_startup: bool = False

    @property
    def sqlalchemy_database_url(self) -> str:
        return normalize_database_url(self.database_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
