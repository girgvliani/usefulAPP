from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    frontend_origin: str = "http://localhost:5173"
    environment: str = "development"
    timezone: str = "Asia/Tbilisi"  # decides what "today" means for daily logs and stats
    gemini_api_key: str | None = None  # meal photos; without it, photo logging is switched off
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.5-flash-lite"  # used when the main model hits its free daily limit

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("database_url")
    @classmethod
    def use_psycopg3(cls, url: str) -> str:
        """Name the Postgres driver explicitly. Railway hands out a plain postgresql:// URL, and which
        driver that means changed between SQLAlchemy releases (psycopg2 in 2.0, psycopg 3 in 2.1)."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
