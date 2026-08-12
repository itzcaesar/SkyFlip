"""Add persistent hourly and daily Bazaar chart rollups.

Revision ID: 0003_history_rollups
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_history_rollups"
down_revision = "0002_local_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bazaar_history_rollups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "product_id",
            sa.String(length=96),
            sa.ForeignKey("bazaar_products.product_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("flip_type", sa.String(length=48), nullable=False),
        sa.Column("interval", sa.String(length=8), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("buy_open", sa.Numeric(20, 8), nullable=False),
        sa.Column("buy_high", sa.Numeric(20, 8), nullable=False),
        sa.Column("buy_low", sa.Numeric(20, 8), nullable=False),
        sa.Column("buy_close", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_open", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_high", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_low", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("liquidity", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column(
            "opportunity_score", sa.Numeric(8, 4), nullable=False, server_default="0"
        ),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_updated_ms", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "product_id",
            "flip_type",
            "interval",
            "bucket_start",
            name="uq_bazaar_history_rollup_bucket",
        ),
    )
    op.create_index(
        "ix_bazaar_history_rollup_lookup",
        "bazaar_history_rollups",
        ["product_id", "flip_type", "interval", "bucket_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_bazaar_history_rollup_lookup", table_name="bazaar_history_rollups")
    op.drop_table("bazaar_history_rollups")
