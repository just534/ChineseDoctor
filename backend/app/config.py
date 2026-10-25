from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "倪海厦经方中医"
    environment: str = "development"  # development | production
    debug: bool = False

    database_url: str = f"sqlite:///{BASE_DIR / 'data.db'}"

    # JWT
    secret_key: str = "change-me-in-production-0000000000"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # Bootstrap administrator (only used when no super admin exists yet)
    admin_username: str = "admin"
    admin_password: str | None = None
    admin_email: str = "admin@example.com"

    allow_registration: bool = True
    default_role: str = "member"

    # Login protection
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # CORS (comma separated); not needed when frontend is served behind the same nginx
    cors_origins: str = ""

    # Content import / startup initialisation (disable when running multiple workers)
    content_dir: Path = BASE_DIR / "content"
    auto_import: bool = True

    # AI consultation (optional)
    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-5-5"
    ai_max_tokens: int = 4096
    ai_daily_limit: int = 30  # per user per day; super admins unlimited

    @field_validator("secret_key")
    @classmethod
    def _secret_len(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY 至少需要 32 个字符")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_production and s.secret_key.startswith("change-me"):
        raise RuntimeError("生产环境必须设置 SECRET_KEY")
    return s
