from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthComponent(BaseModel):
    status: Literal["ok", "degraded", "unavailable", "not_configured"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    service: str
    database: HealthComponent
    redis: HealthComponent
    worker: HealthComponent
    bazaar: HealthComponent
    checked_at: datetime


class FreshnessResponse(BaseModel):
    status: Literal["LIVE", "DELAYED", "STALE", "UNAVAILABLE"]
    source: Literal["hypixel", "demo"] | None = None
    last_success_at: datetime | None = None
    age_seconds: int | None = None
    message: str


class BazaarStatusResponse(BaseModel):
    freshness: FreshnessResponse
    active_products: int
    qualified_opportunities: int
    last_source_updated_ms: int | None = None


class BazaarOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    product_name: str
    flip_type: Literal["buy_order_to_sell_order", "instant_buy_to_instant_sell"]
    buy_price: float
    sell_price: float
    raw_spread: float
    spread_percentage: float
    gross_profit: float
    estimated_fees: float
    net_profit: float
    roi: float
    buy_volume: int
    sell_volume: int
    transaction_volume: int
    suggested_volume: int
    active_buy_orders: int
    active_sell_orders: int
    orderbook_depth: int
    estimated_liquidity: float
    estimated_fill_time_seconds: int | None
    competition_score: float
    volatility: float | None
    short_term_momentum: float | None
    capital_efficiency: float
    manipulation_risk_score: float
    manipulation_risk: str
    confidence_score: float
    opportunity_score: float
    classification: str
    capital_required: float
    is_qualified: bool
    is_stale: bool
    score_breakdown: dict[str, float | int | None]
    signal_explanations: list[str]
    observed_at: datetime
    source_updated_ms: int


class BazaarOpportunityPage(BaseModel):
    items: list[BazaarOpportunityResponse]
    page: int
    page_size: int
    total: int
    freshness: FreshnessResponse


class BazaarHistoryResponse(BaseModel):
    product_id: str
    flip_type: str
    points: list[dict]
    freshness: FreshnessResponse


class CapitalOptimizeRequest(BaseModel):
    available_capital: float = Field(gt=0)
    risk: Literal["conservative", "balanced", "aggressive"] = "balanced"
    max_fill_time_seconds: int | None = Field(default=None, gt=0)
    minimum_roi: float = Field(default=0, ge=0)
    minimum_liquidity: float = Field(default=0, ge=0, le=100)
    maximum_concurrent_flips: int = Field(default=5, ge=1, le=50)


class CapitalAllocation(BaseModel):
    product_id: str
    product_name: str
    allocation: float
    expected_net_profit: float
    opportunity_score: float
    estimated_fill_time_seconds: int | None
    risk: str


class CapitalOptimizeResponse(BaseModel):
    available_capital: float
    allocations: list[CapitalAllocation]
    reserve: float
    projected_net_profit: float
    is_estimate: bool = True


FlipType = Literal["buy_order_to_sell_order", "instant_buy_to_instant_sell"]


class WatchlistCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=96)
    flip_type: FlipType = "buy_order_to_sell_order"
    min_score: float = Field(default=70, ge=0, le=100)
    min_profit: float = Field(default=0, ge=0)
    min_roi: float = Field(default=0, ge=0)


class WatchlistResponse(BaseModel):
    id: int
    product_id: str
    product_name: str
    flip_type: FlipType
    min_score: float
    min_profit: float
    min_roi: float
    is_active: bool
    created_at: datetime
    current_opportunity: BazaarOpportunityResponse | None = None


class AlertResponse(BaseModel):
    id: int
    market: str
    item_key: str
    alert_type: str
    severity: str
    description: str
    estimated_profit: float | None
    confidence: float | None
    risk: str | None
    is_read: bool
    created_at: datetime


class MarketSettingsResponse(BaseModel):
    sell_fee_rate: float
    buy_fee_rate: float
    stale_after_seconds: int
    max_signal_roi_percent: float
    max_price_ratio: float
    history_retention_days: int
    snapshot_retention_days: int
    persisted_overrides: list[str]


class MarketSettingsUpdate(BaseModel):
    sell_fee_rate: float | None = Field(default=None, ge=0, lt=1)
    buy_fee_rate: float | None = Field(default=None, ge=0, lt=1)
    stale_after_seconds: int | None = Field(default=None, ge=15, le=86_400)
    max_signal_roi_percent: float | None = Field(default=None, ge=100, le=1_000_000)
    max_price_ratio: float | None = Field(default=None, ge=2, le=10_000)
    history_retention_days: int | None = Field(default=None, ge=1, le=365)
    snapshot_retention_days: int | None = Field(default=None, ge=1, le=3_650)


class ItemValuationResponse(BaseModel):
    product_id: str
    product_name: str
    freshness: FreshnessResponse
    current_buy_order: float | None
    current_sell_order: float | None
    instant_buy_price: float | None
    instant_sell_price: float | None
    observed_low: float | None
    observed_high: float | None
    observed_median: float | None
    price_change_percent: float | None
    volatility_percent: float | None
    liquidity: float | None
    confidence: float | None
    risk: str | None
    history_points: int
