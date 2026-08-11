from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthComponent(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
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
