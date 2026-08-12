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

    # Development defaults are intentionally self-contained. Docker/PostgreSQL/Redis can
    # still override these values for deployment or integration testing.
    database_url: str = "sqlite+aiosqlite:///./data/skyflip.db"
    redis_url: str | None = None
    auto_create_schema: bool = True
    local_collector_enabled: bool = False

    hypixel_api_key: str | None = None
    hypixel_base_url: str = Field(default="https://api.hypixel.net")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    local_demo_enabled: bool = False

    bazaar_sell_fee_rate: float = Field(default=0.0125, ge=0, lt=1)
    bazaar_buy_fee_rate: float = Field(default=0.0, ge=0, lt=1)
    # A small execution buffer accounts for quote movement/relisting between observation
    # and fill. It is deliberately separate from the platform fee rates.
    bazaar_fee_buffer_rate: float = Field(default=0.0025, ge=0, lt=1)
    bazaar_stale_after_seconds: int = Field(default=120, ge=15)
    bazaar_poll_seconds: int = Field(default=30, ge=5)
    bazaar_max_retries: int = Field(default=3, ge=1, le=8)
    bazaar_max_signal_roi_percent: float = Field(default=500.0, ge=100, le=1_000_000)
    # Live sampling showed the current 10x gate still admitted obvious quote gaps;
    # keep a 5x ceiling until the market-specific baselines have more coverage.
    bazaar_max_price_ratio: float = Field(default=5.0, ge=2, le=10_000)
    bazaar_min_signal_roi_percent: float = Field(default=1.0, ge=0, le=100_000)
    bazaar_min_signal_net_profit: float = Field(default=0.0, ge=0, le=1_000_000_000)
    bazaar_min_signal_liquidity: float = Field(default=20.0, ge=0, le=100)
    bazaar_min_signal_confidence: float = Field(default=55.0, ge=0, le=100)
    bazaar_history_anomaly_min_samples: int = Field(default=12, ge=3, le=2_000)
    bazaar_history_anomaly_zscore: float = Field(default=6.0, ge=2, le=25)
    bazaar_history_max_deviation_percent: float = Field(default=50.0, ge=5, le=1_000)
    bazaar_history_retention_days: int = Field(default=7, ge=1, le=365)
    bazaar_chart_retention_days: int = Field(default=90, ge=7, le=3_650)
    bazaar_snapshot_retention_days: int = Field(default=30, ge=1, le=3_650)

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
