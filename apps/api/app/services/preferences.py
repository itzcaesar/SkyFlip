from collections.abc import Mapping

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import AppSetting

SETTING_TO_CONFIG = {
    "sell_fee_rate": "bazaar_sell_fee_rate",
    "buy_fee_rate": "bazaar_buy_fee_rate",
    "fee_buffer_rate": "bazaar_fee_buffer_rate",
    "stale_after_seconds": "bazaar_stale_after_seconds",
    "max_signal_roi_percent": "bazaar_max_signal_roi_percent",
    "max_price_ratio": "bazaar_max_price_ratio",
    "min_signal_roi_percent": "bazaar_min_signal_roi_percent",
    "min_signal_net_profit": "bazaar_min_signal_net_profit",
    "min_signal_liquidity": "bazaar_min_signal_liquidity",
    "min_signal_confidence": "bazaar_min_signal_confidence",
    "history_anomaly_min_samples": "bazaar_history_anomaly_min_samples",
    "history_anomaly_zscore": "bazaar_history_anomaly_zscore",
    "history_max_deviation_percent": "bazaar_history_max_deviation_percent",
    "history_retention_days": "bazaar_history_retention_days",
    "chart_retention_days": "bazaar_chart_retention_days",
    "snapshot_retention_days": "bazaar_snapshot_retention_days",
}

FLOAT_SETTINGS = {
    "sell_fee_rate",
    "buy_fee_rate",
    "fee_buffer_rate",
    "max_signal_roi_percent",
    "max_price_ratio",
    "min_signal_roi_percent",
    "min_signal_net_profit",
    "min_signal_liquidity",
    "min_signal_confidence",
    "history_anomaly_zscore",
    "history_max_deviation_percent",
}


def _default_values(settings: Settings) -> dict[str, float | int]:
    return {
        "sell_fee_rate": settings.bazaar_sell_fee_rate,
        "buy_fee_rate": settings.bazaar_buy_fee_rate,
        "fee_buffer_rate": settings.bazaar_fee_buffer_rate,
        "stale_after_seconds": settings.bazaar_stale_after_seconds,
        "max_signal_roi_percent": settings.bazaar_max_signal_roi_percent,
        "max_price_ratio": settings.bazaar_max_price_ratio,
        "min_signal_roi_percent": settings.bazaar_min_signal_roi_percent,
        "min_signal_net_profit": settings.bazaar_min_signal_net_profit,
        "min_signal_liquidity": settings.bazaar_min_signal_liquidity,
        "min_signal_confidence": settings.bazaar_min_signal_confidence,
        "history_anomaly_min_samples": settings.bazaar_history_anomaly_min_samples,
        "history_anomaly_zscore": settings.bazaar_history_anomaly_zscore,
        "history_max_deviation_percent": settings.bazaar_history_max_deviation_percent,
        "history_retention_days": settings.bazaar_history_retention_days,
        "chart_retention_days": settings.bazaar_chart_retention_days,
        "snapshot_retention_days": settings.bazaar_snapshot_retention_days,
    }


async def _stored_values(session: AsyncSession) -> dict[str, str]:
    rows = (await session.scalars(select(AppSetting))).all()
    return {row.key: row.value for row in rows if row.key in SETTING_TO_CONFIG}


async def get_runtime_settings(session: AsyncSession, settings: Settings) -> Settings:
    """Apply local database overrides without exposing or mutating environment secrets."""

    stored = await _stored_values(session)
    updates: dict[str, float | int] = {}
    for key, config_key in SETTING_TO_CONFIG.items():
        if key not in stored:
            continue
        try:
            updates[config_key] = float(stored[key]) if key in FLOAT_SETTINGS else int(stored[key])
        except (TypeError, ValueError):
            continue
    return settings.model_copy(update=updates)


async def market_settings_response(session: AsyncSession, settings: Settings) -> dict:
    stored = await _stored_values(session)
    effective = await get_runtime_settings(session, settings)
    return {
        "sell_fee_rate": effective.bazaar_sell_fee_rate,
        "buy_fee_rate": effective.bazaar_buy_fee_rate,
        "fee_buffer_rate": effective.bazaar_fee_buffer_rate,
        "stale_after_seconds": effective.bazaar_stale_after_seconds,
        "max_signal_roi_percent": effective.bazaar_max_signal_roi_percent,
        "max_price_ratio": effective.bazaar_max_price_ratio,
        "min_signal_roi_percent": effective.bazaar_min_signal_roi_percent,
        "min_signal_net_profit": effective.bazaar_min_signal_net_profit,
        "min_signal_liquidity": effective.bazaar_min_signal_liquidity,
        "min_signal_confidence": effective.bazaar_min_signal_confidence,
        "history_anomaly_min_samples": effective.bazaar_history_anomaly_min_samples,
        "history_anomaly_zscore": effective.bazaar_history_anomaly_zscore,
        "history_max_deviation_percent": effective.bazaar_history_max_deviation_percent,
        "history_retention_days": effective.bazaar_history_retention_days,
        "chart_retention_days": effective.bazaar_chart_retention_days,
        "snapshot_retention_days": effective.bazaar_snapshot_retention_days,
        "persisted_overrides": sorted(stored),
    }


async def update_market_settings(
    session: AsyncSession, settings: Settings, updates: Mapping[str, float | int]
) -> dict:
    for key, value in updates.items():
        if key not in SETTING_TO_CONFIG:
            continue
        row = await session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=str(value))
            session.add(row)
        else:
            row.value = str(value)
    await session.commit()
    return await market_settings_response(session, settings)


async def reset_market_settings(session: AsyncSession, settings: Settings) -> dict:
    await session.execute(delete(AppSetting).where(AppSetting.key.in_(SETTING_TO_CONFIG)))
    await session.commit()
    return await market_settings_response(session, settings)
