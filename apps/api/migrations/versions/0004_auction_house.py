"""Add local Auction House listings and comparable observations.

Revision ID: 0004_auction_house
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_auction_house"
down_revision = "0003_history_rollups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auction_house_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_ms", sa.BigInteger(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("auction_count", sa.Integer(), nullable=False),
        sa.Column("bin_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="hypixel"),
    )
    op.create_index(
        "ix_auction_house_snapshots_fetched_at",
        "auction_house_snapshots",
        ["fetched_at"],
    )

    op.create_table(
        "auction_listings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("auction_uuid", sa.String(length=64), nullable=False, unique=True),
        sa.Column("item_uuid", sa.String(length=64), nullable=True),
        sa.Column("item_name", sa.String(length=160), nullable=False),
        sa.Column("normalized_item_id", sa.String(length=160), nullable=False),
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=False),
        sa.Column("item_fingerprint", sa.JSON(), nullable=False),
        sa.Column("item_lore", sa.Text(), nullable=True),
        sa.Column("extra", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=48), nullable=False, server_default="misc"),
        sa.Column("tier", sa.String(length=24), nullable=False, server_default="COMMON"),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("is_bin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_source_updated_ms", sa.BigInteger(), nullable=False),
        sa.Column("last_snapshot_hash", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_auction_listings_active_item",
        "auction_listings",
        ["is_active", "normalized_item_id"],
    )
    op.create_index(
        "ix_auction_listings_active_fingerprint",
        "auction_listings",
        ["is_active", "fingerprint_hash"],
    )
    op.create_index("ix_auction_listings_end_at", "auction_listings", ["end_at"])

    op.create_table(
        "auction_market_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_ms", sa.BigInteger(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("normalized_item_id", sa.String(length=160), nullable=False),
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=False),
        sa.Column("item_name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=48), nullable=False, server_default="misc"),
        sa.Column("tier", sa.String(length=24), nullable=False, server_default="COMMON"),
        sa.Column("listing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("median_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("high_price", sa.Numeric(20, 8), nullable=False),
        sa.UniqueConstraint(
            "normalized_item_id",
            "fingerprint_hash",
            "source_updated_ms",
            name="uq_auction_market_observation_source",
        ),
    )
    op.create_index(
        "ix_auction_market_observations_lookup",
        "auction_market_observations",
        ["normalized_item_id", "fingerprint_hash", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auction_market_observations_lookup",
        table_name="auction_market_observations",
    )
    op.drop_table("auction_market_observations")
    op.drop_index("ix_auction_listings_end_at", table_name="auction_listings")
    op.drop_index(
        "ix_auction_listings_active_fingerprint",
        table_name="auction_listings",
    )
    op.drop_index("ix_auction_listings_active_item", table_name="auction_listings")
    op.drop_table("auction_listings")
    op.drop_index(
        "ix_auction_house_snapshots_fetched_at",
        table_name="auction_house_snapshots",
    )
    op.drop_table("auction_house_snapshots")
