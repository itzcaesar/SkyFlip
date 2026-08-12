from app.services.bazaar_engine import (
    BUY_ORDER_TO_SELL_ORDER,
    INSTANT_BUY_TO_INSTANT_SELL,
    BazaarFeePolicy,
    compute_bazaar_opportunities,
)


def sample_product() -> dict:
    return {
        "sell_summary": [{"price": 110, "amount": 900, "orders": 4}],
        "buy_summary": [{"price": 100, "amount": 800, "orders": 3}],
        "quick_status": {
            "buyPrice": 110,
            "sellPrice": 100,
            "buyVolume": 1200,
            "sellVolume": 1000,
            "buyOrders": 6,
            "sellOrders": 5,
            "buyMovingWeek": 100_000,
            "sellMovingWeek": 110_000,
        },
    }


def test_bazaar_calculation_includes_fees_and_distinguishes_strategies() -> None:
    results = compute_bazaar_opportunities(
        "ENCHANTED_DIAMOND",
        sample_product(),
        fee_policy=BazaarFeePolicy(buy_fee_rate=0, sell_fee_rate=0.01),
    )
    order_flip = next(result for result in results if result.flip_type == BUY_ORDER_TO_SELL_ORDER)
    instant_flip = next(
        result for result in results if result.flip_type == INSTANT_BUY_TO_INSTANT_SELL
    )

    assert order_flip.buy_price == 100
    assert order_flip.sell_price == 110
    assert order_flip.raw_spread == 10
    assert order_flip.estimated_fees == 1.1
    assert order_flip.net_profit == 8.9
    assert order_flip.roi == 8.9
    assert order_flip.suggested_volume == 50
    assert order_flip.estimated_fill_time_seconds is not None
    assert instant_flip.buy_price == 110
    assert instant_flip.sell_price == 100
    assert instant_flip.net_profit < 0
    assert order_flip.opportunity_score > instant_flip.opportunity_score


def test_zero_volume_is_not_presented_as_a_qualified_flip() -> None:
    product = sample_product()
    product["quick_status"]["buyVolume"] = 0
    product["quick_status"]["sellVolume"] = 0
    results = compute_bazaar_opportunities("RARE_ITEM", product)

    assert results
    assert all(result.suggested_volume == 0 for result in results)
    assert all(result.is_qualified is False for result in results)
    assert all(result.manipulation_risk in {"HIGH", "EXTREME"} for result in results)


def test_missing_price_fields_produce_no_fabricated_result() -> None:
    assert compute_bazaar_opportunities("MISSING", {"quick_status": {}}) == []


def test_sanity_limits_keep_extreme_quotes_out_of_qualified_signals() -> None:
    product = sample_product()
    product["quick_status"]["sellPrice"] = 100
    product["quick_status"]["buyPrice"] = 10_000
    results = compute_bazaar_opportunities("ANOMALOUS", product)
    order_flip = next(result for result in results if result.flip_type == BUY_ORDER_TO_SELL_ORDER)

    assert order_flip.is_qualified is False
    assert order_flip.manipulation_risk in {"HIGH", "EXTREME"}
    assert any("sanity limit" in explanation for explanation in order_flip.signal_explanations)


def test_history_supplies_volatility_and_momentum() -> None:
    results = compute_bazaar_opportunities(
        "HISTORY_ITEM",
        sample_product(),
        history_prices=[(100, 100), (100, 110), (100, 121)],
        history_samples=3,
    )
    order_flip = next(result for result in results if result.flip_type == BUY_ORDER_TO_SELL_ORDER)

    assert order_flip.volatility is not None
    assert order_flip.short_term_momentum == 21


def test_history_outlier_is_not_a_qualified_signal() -> None:
    history = [(100, 100)] * 12
    product = sample_product()
    product["quick_status"]["buyPrice"] = 200
    product["quick_status"]["sellPrice"] = 100
    results = compute_bazaar_opportunities(
        "HISTORY_ANOMALY",
        product,
        history_samples=12,
        history_prices_by_flip={BUY_ORDER_TO_SELL_ORDER: history},
        history_samples_by_flip={BUY_ORDER_TO_SELL_ORDER: 12},
        history_max_deviation_percent=50,
    )
    order_flip = next(result for result in results if result.flip_type == BUY_ORDER_TO_SELL_ORDER)

    assert order_flip.is_qualified is False
    assert order_flip.manipulation_risk in {"HIGH", "EXTREME"}
    assert any("recent median" in explanation for explanation in order_flip.signal_explanations)


def test_signal_policy_applies_execution_buffer_and_minimums() -> None:
    results = compute_bazaar_opportunities(
        "POLICY_ITEM",
        sample_product(),
        fee_policy=BazaarFeePolicy(buy_fee_rate=0, sell_fee_rate=0.01, buffer_rate=0.002),
        min_signal_roi_percent=10,
        min_signal_liquidity=95,
    )
    order_flip = next(result for result in results if result.flip_type == BUY_ORDER_TO_SELL_ORDER)

    assert order_flip.estimated_fees == 1.52
    assert order_flip.is_qualified is False
    assert any("signal threshold" in explanation for explanation in order_flip.signal_explanations)
