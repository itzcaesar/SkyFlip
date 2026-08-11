"""Create the Phase 1 and Bazaar vertical-slice schema.

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bazaar_products",
        sa.Column("product_id", sa.String(length=96), primary_key=True),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_source_updated_ms", sa.BigInteger(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_payload_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "bazaar_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_ms", sa.BigInteger(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("product_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="hypixel"),
    )
    op.create_index("ix_bazaar_snapshots_fetched_at", "bazaar_snapshots", ["fetched_at"])
    op.create_table(
        "bazaar_opportunities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.String(length=96), sa.ForeignKey("bazaar_products.product_id", ondelete="CASCADE"), nullable=False),
        sa.Column("flip_type", sa.String(length=48), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_ms", sa.BigInteger(), nullable=False),
        sa.Column("buy_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("raw_spread", sa.Numeric(20, 8), nullable=False),
        sa.Column("spread_percentage", sa.Numeric(12, 6), nullable=False),
        sa.Column("gross_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column("estimated_fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("net_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column("roi", sa.Numeric(12, 6), nullable=False),
        sa.Column("buy_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sell_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transaction_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suggested_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_buy_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_sell_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("orderbook_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_liquidity", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("estimated_fill_time_seconds", sa.Integer(), nullable=True),
        sa.Column("competition_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("volatility", sa.Numeric(8, 4), nullable=True),
        sa.Column("short_term_momentum", sa.Numeric(8, 4), nullable=True),
        sa.Column("capital_efficiency", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("manipulation_risk_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("manipulation_risk", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("confidence_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("opportunity_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("classification", sa.String(length=16), nullable=False, server_default="Weak"),
        sa.Column("capital_required", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("is_qualified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("signal_explanations", sa.JSON(), nullable=False),
        sa.UniqueConstraint("product_id", "flip_type", name="uq_bazaar_opportunity_product_flip"),
    )
    op.create_index("ix_bazaar_opportunities_score", "bazaar_opportunities", ["opportunity_score"])
    op.create_index("ix_bazaar_opportunities_observed_at", "bazaar_opportunities", ["observed_at"])
    op.create_index(
        "ix_bazaar_opportunities_filters",
        "bazaar_opportunities",
        ["is_qualified", "is_stale", "manipulation_risk"],
    )
    op.create_table(
        "bazaar_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.String(length=96), sa.ForeignKey("bazaar_products.product_id", ondelete="CASCADE"), nullable=False),
        sa.Column("flip_type", sa.String(length=48), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("buy_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("spread", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("liquidity", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("opportunity_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("source_updated_ms", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "ix_bazaar_history_product_time",
        "bazaar_history",
        ["product_id", "flip_type", "observed_at"],
    )
    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market", sa.String(length=24), nullable=False),
        sa.Column("item_key", sa.String(length=160), nullable=False),
        sa.Column("alert_type", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=True),
        sa.Column("risk", sa.String(length=16), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_alert_events_created_at", "alert_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_created_at", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_bazaar_history_product_time", table_name="bazaar_history")
    op.drop_table("bazaar_history")
    op.drop_index("ix_bazaar_opportunities_filters", table_name="bazaar_opportunities")
    op.drop_index("ix_bazaar_opportunities_observed_at", table_name="bazaar_opportunities")
    op.drop_index("ix_bazaar_opportunities_score", table_name="bazaar_opportunities")
    op.drop_table("bazaar_opportunities")
    op.drop_index("ix_bazaar_snapshots_fetched_at", table_name="bazaar_snapshots")
    op.drop_table("bazaar_snapshots")
    op.drop_table("bazaar_products")

