from dataclasses import dataclass
from statistics import median, pstdev
from typing import Any

from .scoring import BazaarScoreInput, clamp, classify_risk, score_bazaar_opportunity

BUY_ORDER_TO_SELL_ORDER = "buy_order_to_sell_order"
INSTANT_BUY_TO_INSTANT_SELL = "instant_buy_to_instant_sell"


@dataclass(frozen=True)
class BazaarFeePolicy:
    buy_fee_rate: float = 0.0
    sell_fee_rate: float = 0.0125
    buffer_rate: float = 0.0


@dataclass(frozen=True)
class BazaarResult:
    product_id: str
    flip_type: str
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
    score_breakdown: dict[str, float]
    signal_explanations: list[str]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else default
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def humanize_product_id(product_id: str) -> str:
    return " ".join(word.capitalize() for word in product_id.replace("-", "_").split("_"))


def _levels(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [level for level in payload if isinstance(level, dict)]


def _level_price(levels: list[dict[str, Any]], *, lowest: bool) -> float | None:
    prices = [_number(level.get("price"), -1) for level in levels]
    prices = [price for price in prices if price >= 0]
    if not prices:
        return None
    return min(prices) if lowest else max(prices)


def _level_depth(levels: list[dict[str, Any]]) -> int:
    return sum(_integer(level.get("amount")) for level in levels[:5])


def _make_result(
    product_id: str,
    *,
    flip_type: str,
    buy_price: float,
    sell_price: float,
    quick: dict[str, Any],
    buy_levels: list[dict[str, Any]],
    sell_levels: list[dict[str, Any]],
    fee_policy: BazaarFeePolicy,
    history_samples: int = 0,
    history_prices: list[tuple[float, float]] | None = None,
    max_reasonable_roi_percent: float = 1_000.0,
    max_price_ratio: float = 50.0,
    min_signal_roi_percent: float = 0.0,
    min_signal_net_profit: float = 0.0,
    min_signal_liquidity: float = 0.0,
    min_signal_confidence: float = 50.0,
    history_anomaly_min_samples: int = 12,
    history_anomaly_zscore: float = 6.0,
    history_max_deviation_percent: float = 50.0,
) -> BazaarResult:
    raw_spread = sell_price - buy_price
    spread_percentage = raw_spread / buy_price * 100 if buy_price > 0 else 0.0
    gross_profit = raw_spread
    effective_buy_fee_rate = fee_policy.buy_fee_rate + fee_policy.buffer_rate
    effective_sell_fee_rate = fee_policy.sell_fee_rate + fee_policy.buffer_rate
    estimated_fees = buy_price * effective_buy_fee_rate + sell_price * effective_sell_fee_rate
    net_profit = gross_profit - estimated_fees
    roi = net_profit / buy_price * 100 if buy_price > 0 else 0.0

    buy_volume = _integer(quick.get("buyVolume"))
    sell_volume = _integer(quick.get("sellVolume"))
    transaction_volume = min(buy_volume, sell_volume)
    if transaction_volume <= 0:
        suggested_volume = 0
    else:
        suggested_volume = max(1, min(10_000, int(transaction_volume * 0.05)))
    active_buy_orders = _integer(
        quick.get("buyOrders"), sum(_integer(level.get("orders")) for level in buy_levels)
    )
    active_sell_orders = _integer(
        quick.get("sellOrders"), sum(_integer(level.get("orders")) for level in sell_levels)
    )
    orderbook_depth = _level_depth(buy_levels) + _level_depth(sell_levels)

    volume_score = clamp(transaction_volume / max(suggested_volume * 20, 1), 0, 1)
    depth_score = clamp(orderbook_depth / max(suggested_volume * 10, 1), 0, 1)
    order_score = clamp((active_buy_orders + active_sell_orders) / 20, 0, 1)
    estimated_liquidity = round(
        (volume_score * 0.5 + depth_score * 0.35 + order_score * 0.15) * 100, 2
    )

    moving_week = max(_number(quick.get("buyMovingWeek")), _number(quick.get("sellMovingWeek")))
    estimated_fill_time_seconds = None
    if moving_week > 0 and suggested_volume > 0:
        units_per_second = moving_week / (7 * 24 * 60 * 60)
        estimated_fill_time_seconds = max(60, int(suggested_volume / units_per_second))

    competition_score = round(clamp((active_buy_orders + active_sell_orders) / 25 * 100), 2)
    recent_history = (history_prices or [])[-60:]
    historical_buy_prices = [buy for buy, _ in recent_history if buy > 0]
    historical_sell_prices = [sell for _, sell in recent_history if sell > 0]
    returns = [
        (current - previous) / previous * 100
        for previous, current in zip(
            historical_sell_prices, historical_sell_prices[1:], strict=False
        )
        if previous > 0
    ]
    volatility = round(min(100, pstdev(returns)), 2) if returns else None
    momentum = None
    if len(historical_sell_prices) >= 2 and historical_sell_prices[0] > 0:
        momentum = round(
            clamp((historical_sell_prices[-1] / historical_sell_prices[0] - 1) * 100, -100, 100),
            2,
        )
    capital_efficiency = round(clamp(roi * 5), 2)

    manipulation_risk_score = 15.0
    if transaction_volume == 0 or orderbook_depth == 0:
        manipulation_risk_score += 55
    elif transaction_volume < 10:
        manipulation_risk_score += 25
    if active_buy_orders + active_sell_orders < 2:
        manipulation_risk_score += 20
    if raw_spread <= 0:
        manipulation_risk_score += 10
    anomaly_reasons: list[str] = []
    if volatility is not None:
        if volatility >= 50:
            manipulation_risk_score += 25
        elif volatility >= 20:
            manipulation_risk_score += 12
    price_ratio = sell_price / buy_price if buy_price > 0 else 0
    if raw_spread <= 0:
        anomaly_reasons.append("The exit quote is not above the entry quote.")
    if roi > max_reasonable_roi_percent:
        anomaly_reasons.append(
            f"ROI exceeds the {max_reasonable_roi_percent:,.0f}% sanity limit."
        )
    if price_ratio > max_price_ratio:
        anomaly_reasons.append(
            f"Quote ratio is {price_ratio:,.1f}x, above the {max_price_ratio:,.0f}x sanity limit."
        )

    def history_outlier_reason(label: str, current: float, samples: list[float]) -> str | None:
        if len(samples) < history_anomaly_min_samples or current <= 0:
            return None
        baseline = median(samples)
        if baseline <= 0:
            return None
        deviations = [abs(value - baseline) for value in samples]
        mad = median(deviations)
        # A one-percent floor prevents a flat market from producing a zero scale while
        # still making a large one-cycle jump obvious after enough observations.
        scale = max(1.4826 * mad, baseline * 0.01)
        robust_z = abs(current - baseline) / scale
        deviation_percent = abs(current / baseline - 1) * 100
        if (
            deviation_percent >= history_max_deviation_percent
            and robust_z >= history_anomaly_zscore
        ):
            return (
                f"{label} quote is {deviation_percent:,.0f}% from the {baseline:,.4g} "
                f"recent median ({len(samples)} samples, robust z={robust_z:,.1f})."
            )
        return None

    for label, current, samples in (
        ("Entry", buy_price, historical_buy_prices),
        ("Exit", sell_price, historical_sell_prices),
    ):
        reason = history_outlier_reason(label, current, samples)
        if reason:
            anomaly_reasons.append(reason)
    if anomaly_reasons:
        manipulation_risk_score = max(manipulation_risk_score + 35, 85)
    manipulation_risk_score = round(clamp(manipulation_risk_score), 2)
    manipulation_risk = classify_risk(manipulation_risk_score)

    confidence_score = 35.0
    confidence_score += 20 if buy_price > 0 and sell_price > 0 else 0
    confidence_score += 10 if buy_volume or sell_volume else 0
    confidence_score += 10 if active_buy_orders or active_sell_orders else 0
    confidence_score += 5 if moving_week > 0 else 0
    # Confidence grows with repeated live observations, but does not become near-certain
    # after only a handful of identical polls.
    confidence_cap = (
        68.0
        if history_samples < 3
        else 78.0
        if history_samples < history_anomaly_min_samples
        else 88.0
        if history_samples < 30
        else 94.0
    )
    confidence_score = min(confidence_cap, confidence_score + min(history_samples, 60) * 0.25)
    confidence_score = round(clamp(confidence_score), 2)
    if anomaly_reasons:
        confidence_score = min(confidence_score, 35.0)

    score = score_bazaar_opportunity(
        BazaarScoreInput(
            buy_price=buy_price,
            net_profit=net_profit,
            roi_percent=roi,
            liquidity=estimated_liquidity,
            transaction_volume=transaction_volume,
            suggested_volume=suggested_volume,
            confidence=confidence_score,
            competition=competition_score,
            volatility=volatility,
            manipulation_risk=manipulation_risk_score,
            fill_time_seconds=estimated_fill_time_seconds,
        )
    )
    capital_required = buy_price * suggested_volume
    explanations: list[str] = []
    if raw_spread > 0:
        explanations.append(f"Gross spread is {raw_spread:,.4g} coins per unit before fees.")
    else:
        explanations.append("The exit price is not above the entry price after current quotes.")
    if transaction_volume > 0:
        explanations.append(
            f"Immediately visible two-sided volume is {transaction_volume:,} units."
        )
    else:
        explanations.append("No two-sided volume was reported; fill probability is unavailable.")
    if history_samples == 0:
        explanations.append(
            "Confidence is capped because historical observations are not available yet."
        )
    elif history_samples < history_anomaly_min_samples:
        explanations.append(
            f"History has {history_samples} live samples; anomaly checks activate at "
            f"{history_anomaly_min_samples}."
        )
    if fee_policy.buffer_rate > 0:
        explanations.append(
            f"Estimated fees include a {fee_policy.buffer_rate * 100:.2f}% execution buffer."
        )
    if roi < min_signal_roi_percent:
        explanations.append(f"ROI is below the {min_signal_roi_percent:.2f}% signal threshold.")
    if net_profit < min_signal_net_profit:
        explanations.append(
            f"Net profit is below the {min_signal_net_profit:,.4g} coin signal threshold."
        )
    if estimated_liquidity < min_signal_liquidity:
        explanations.append(
            f"Liquidity is below the {min_signal_liquidity:.0f}/100 signal threshold."
        )
    if confidence_score < min_signal_confidence:
        explanations.append(
            f"Confidence is below the {min_signal_confidence:.0f}% signal threshold."
        )
    for reason in anomaly_reasons:
        explanations.append(f"Sanity check: {reason} Treat this quote as an anomaly.")
    if manipulation_risk_score >= 60:
        explanations.append("Thin order-book evidence increases manipulation/anomaly risk.")

    return BazaarResult(
        product_id=product_id,
        flip_type=flip_type,
        buy_price=round(buy_price, 8),
        sell_price=round(sell_price, 8),
        raw_spread=round(raw_spread, 8),
        spread_percentage=round(spread_percentage, 6),
        gross_profit=round(gross_profit, 8),
        estimated_fees=round(estimated_fees, 8),
        net_profit=round(net_profit, 8),
        roi=round(roi, 6),
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        transaction_volume=transaction_volume,
        suggested_volume=suggested_volume,
        active_buy_orders=active_buy_orders,
        active_sell_orders=active_sell_orders,
        orderbook_depth=orderbook_depth,
        estimated_liquidity=estimated_liquidity,
        estimated_fill_time_seconds=estimated_fill_time_seconds,
        competition_score=competition_score,
        volatility=volatility,
        short_term_momentum=momentum,
        capital_efficiency=capital_efficiency,
        manipulation_risk_score=manipulation_risk_score,
        manipulation_risk=manipulation_risk,
        confidence_score=confidence_score,
        opportunity_score=score.score,
        classification=score.classification,
        capital_required=round(capital_required, 8),
        is_qualified=(
            net_profit >= min_signal_net_profit
            and roi >= min_signal_roi_percent
            and suggested_volume > 0
            and estimated_liquidity >= min_signal_liquidity
            and confidence_score >= min_signal_confidence
            and not anomaly_reasons
        ),
        score_breakdown=score.breakdown,
        signal_explanations=explanations,
    )


def compute_bazaar_opportunities(
    product_id: str,
    product: dict[str, Any],
    *,
    fee_policy: BazaarFeePolicy | None = None,
    history_samples: int = 0,
    history_prices: list[tuple[float, float]] | None = None,
    history_prices_by_flip: dict[str, list[tuple[float, float]]] | None = None,
    history_samples_by_flip: dict[str, int] | None = None,
    max_reasonable_roi_percent: float = 1_000.0,
    max_price_ratio: float = 50.0,
    min_signal_roi_percent: float = 0.0,
    min_signal_net_profit: float = 0.0,
    min_signal_liquidity: float = 0.0,
    min_signal_confidence: float = 50.0,
    history_anomaly_min_samples: int = 12,
    history_anomaly_zscore: float = 6.0,
    history_max_deviation_percent: float = 50.0,
) -> list[BazaarResult]:
    """Compute both supported Bazaar strategies from one normalized Hypixel product."""

    raw_quick = product.get("quick_status")
    quick: dict[str, Any] = raw_quick if isinstance(raw_quick, dict) else {}
    sell_levels = _levels(product.get("sell_summary"))
    buy_levels = _levels(product.get("buy_summary"))
    instant_buy = _number(quick.get("buyPrice"), -1)
    instant_sell = _number(quick.get("sellPrice"), -1)
    if instant_buy <= 0:
        instant_buy = _level_price(sell_levels, lowest=True) or -1
    if instant_sell <= 0:
        instant_sell = _level_price(buy_levels, lowest=False) or -1
    if instant_buy <= 0 or instant_sell <= 0:
        return []

    policy = fee_policy or BazaarFeePolicy()
    price_history = history_prices_by_flip or {}
    sample_counts = history_samples_by_flip or {}
    recommended_buy_order = instant_sell
    recommended_sell_order = instant_buy
    return [
        _make_result(
            product_id,
            flip_type=BUY_ORDER_TO_SELL_ORDER,
            buy_price=recommended_buy_order,
            sell_price=recommended_sell_order,
            quick=quick,
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            fee_policy=policy,
            history_samples=sample_counts.get(BUY_ORDER_TO_SELL_ORDER, history_samples),
            history_prices=price_history.get(BUY_ORDER_TO_SELL_ORDER, history_prices or []),
            max_reasonable_roi_percent=max_reasonable_roi_percent,
            max_price_ratio=max_price_ratio,
            min_signal_roi_percent=min_signal_roi_percent,
            min_signal_net_profit=min_signal_net_profit,
            min_signal_liquidity=min_signal_liquidity,
            min_signal_confidence=min_signal_confidence,
            history_anomaly_min_samples=history_anomaly_min_samples,
            history_anomaly_zscore=history_anomaly_zscore,
            history_max_deviation_percent=history_max_deviation_percent,
        ),
        _make_result(
            product_id,
            flip_type=INSTANT_BUY_TO_INSTANT_SELL,
            buy_price=instant_buy,
            sell_price=instant_sell,
            quick=quick,
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            fee_policy=policy,
            history_samples=sample_counts.get(INSTANT_BUY_TO_INSTANT_SELL, history_samples),
            history_prices=price_history.get(INSTANT_BUY_TO_INSTANT_SELL, history_prices or []),
            max_reasonable_roi_percent=max_reasonable_roi_percent,
            max_price_ratio=max_price_ratio,
            min_signal_roi_percent=min_signal_roi_percent,
            min_signal_net_profit=min_signal_net_profit,
            min_signal_liquidity=min_signal_liquidity,
            min_signal_confidence=min_signal_confidence,
            history_anomaly_min_samples=history_anomaly_min_samples,
            history_anomaly_zscore=history_anomaly_zscore,
            history_max_deviation_percent=history_max_deviation_percent,
        ),
    ]
