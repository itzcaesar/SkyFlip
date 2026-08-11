from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BazaarProduct(Base):
    __tablename__ = "bazaar_products"

    product_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_source_updated_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    opportunities: Mapped[list["BazaarOpportunity"]] = relationship(back_populates="product")
    history: Mapped[list["BazaarHistoryPoint"]] = relationship(back_populates="product")


class BazaarSnapshot(Base):
    __tablename__ = "bazaar_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    product_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="hypixel")

    __table_args__ = (Index("ix_bazaar_snapshots_fetched_at", "fetched_at"),)


class BazaarOpportunity(Base):
    __tablename__ = "bazaar_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("bazaar_products.product_id", ondelete="CASCADE"), nullable=False
    )
    flip_type: Mapped[str] = mapped_column(String(48), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    sell_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    raw_spread: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    spread_percentage: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    estimated_fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    roi: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    buy_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sell_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transaction_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suggested_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_buy_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_sell_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orderbook_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_liquidity: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    estimated_fill_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    volatility: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    short_term_momentum: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    capital_efficiency: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    manipulation_risk_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=0
    )
    manipulation_risk: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    opportunity_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    classification: Mapped[str] = mapped_column(String(16), nullable=False, default="Weak")
    capital_required: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    is_qualified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    signal_explanations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    product: Mapped[BazaarProduct] = relationship(back_populates="opportunities")

    __table_args__ = (
        UniqueConstraint("product_id", "flip_type", name="uq_bazaar_opportunity_product_flip"),
        Index("ix_bazaar_opportunities_score", "opportunity_score"),
        Index("ix_bazaar_opportunities_observed_at", "observed_at"),
        Index("ix_bazaar_opportunities_filters", "is_qualified", "is_stale", "manipulation_risk"),
    )


class BazaarHistoryPoint(Base):
    __tablename__ = "bazaar_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("bazaar_products.product_id", ondelete="CASCADE"), nullable=False
    )
    flip_type: Mapped[str] = mapped_column(String(48), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    sell_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    spread: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    liquidity: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    opportunity_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    source_updated_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)

    product: Mapped[BazaarProduct] = relationship(back_populates="history")

    __table_args__ = (
        Index("ix_bazaar_history_product_time", "product_id", "flip_type", "observed_at"),
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(24), nullable=False)
    item_key: Mapped[str] = mapped_column(String(160), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    risk: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_alert_events_created_at", "created_at"),)
