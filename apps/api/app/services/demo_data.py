from datetime import UTC, datetime
from typing import Any

# This catalog is intentionally small and synthetic. It exists only to make the local UI
# usable while a developer is wiring credentials or diagnosing an upstream outage.
_DEMO_CATALOG: tuple[tuple[str, float, float, int, int, int, int, int, int], ...] = (
    ("ENCHANTED_DIAMOND", 110.0, 100.0, 1200, 1000, 6, 5, 100_000, 110_000),
    ("ENCHANTED_IRON", 58.0, 52.0, 9000, 8000, 12, 10, 800_000, 850_000),
    ("ENCHANTED_GOLD", 225.0, 204.0, 5000, 4500, 8, 7, 420_000, 460_000),
    ("ENCHANTED_QUARTZ", 380.0, 335.0, 6000, 5000, 10, 9, 300_000, 330_000),
    ("REFINED_DIAMOND", 8200.0, 7400.0, 1500, 1200, 3, 3, 75_000, 80_000),
    ("MITHRIL", 92.0, 78.0, 2500, 2000, 5, 4, 180_000, 210_000),
)


def _demo_product(
    instant_buy: float,
    instant_sell: float,
    buy_volume: int,
    sell_volume: int,
    buy_orders: int,
    sell_orders: int,
    buy_moving_week: int,
    sell_moving_week: int,
) -> dict[str, Any]:
    return {
        "sell_summary": [{"price": instant_buy, "amount": buy_volume // 2, "orders": buy_orders}],
        "buy_summary": [{"price": instant_sell, "amount": sell_volume // 2, "orders": sell_orders}],
        "quick_status": {
            "buyPrice": instant_buy,
            "sellPrice": instant_sell,
            "buyVolume": buy_volume,
            "sellVolume": sell_volume,
            "buyOrders": buy_orders,
            "sellOrders": sell_orders,
            "buyMovingWeek": buy_moving_week,
            "sellMovingWeek": sell_moving_week,
        },
    }


def demo_bazaar_payload(now: datetime | None = None) -> dict[str, Any]:
    """Return a clearly labelled, deterministic Bazaar-shaped local dataset."""

    observed_at = now or datetime.now(UTC)
    source_updated_ms = int(observed_at.timestamp() * 1000)
    products = {
        product_id: _demo_product(
            instant_buy,
            instant_sell,
            buy_volume,
            sell_volume,
            buy_orders,
            sell_orders,
            buy_moving_week,
            sell_moving_week,
        )
        for (
            product_id,
            instant_buy,
            instant_sell,
            buy_volume,
            sell_volume,
            buy_orders,
            sell_orders,
            buy_moving_week,
            sell_moving_week,
        ) in _DEMO_CATALOG
    }
    return {
        "_fixture_note": "LOCAL DEMO DATA ONLY. These values are not live market prices.",
        "success": True,
        "lastUpdated": source_updated_ms,
        "products": products,
    }
