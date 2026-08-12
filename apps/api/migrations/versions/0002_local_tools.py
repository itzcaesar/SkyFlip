"""Add local watchlists and persisted market settings.

Revision ID: 0002_local_tools
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_local_tools"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "product_id",
            sa.String(length=96),
            sa.ForeignKey("bazaar_products.product_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("flip_type", sa.String(length=48), nullable=False),
        sa.Column("min_score", sa.Numeric(8, 4), nullable=False, server_default="70"),
        sa.Column("min_profit", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("min_roi", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "flip_type", name="uq_watchlist_product_flip"),
    )
    op.create_index("ix_watchlist_active", "watchlist_items", ["is_active"])
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_watchlist_active", table_name="watchlist_items")
    op.drop_table("watchlist_items")
