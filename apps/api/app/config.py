from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, TypeAdapter, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration.

    Secrets are intentionally server-side only. The web app receives only the public API URL.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    app_secret: str = Field(default="change-me-in-development", min_length=1)

    database_url: str = "postgresql+asyncpg://skyflip:skyflip@localhost:5432/skyflip"
    redis_url: str = "redis://localhost:6379/0"

    hypixel_api_key: str | None = None
    hypixel_base_url: str = Field(default="https://api.hypixel.net")
    cors_origins: str = "http://localhost:3000"

    bazaar_sell_fee_rate: float = Field(default=0.0125, ge=0, lt=1)
    bazaar_buy_fee_rate: float = Field(default=0.0, ge=0, lt=1)
    bazaar_stale_after_seconds: int = Field(default=120, ge=15)
    bazaar_poll_seconds: int = Field(default=30, ge=5)
    bazaar_max_retries: int = Field(default=3, ge=1, le=8)

    @field_validator("hypixel_base_url")
    @classmethod
    def validate_hypixel_base_url(cls, value: str) -> str:
        return str(TypeAdapter(AnyHttpUrl).validate_python(value))

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
