from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AppSetting

ALERT_SETTING_KEYS = {
    "alerts_enabled": "enabled",
    "alerts_minimum_severity": "minimum_severity",
    "alerts_cooldown_minutes": "cooldown_minutes",
    "alerts_browser_notifications": "browser_notifications",
}

DEFAULT_ALERT_PREFERENCES: dict[str, bool | int | str] = {
    "enabled": True,
    "minimum_severity": "MEDIUM",
    "cooldown_minutes": 5,
    "browser_notifications": False,
}


def _parse_value(key: str, value: str) -> bool | int | str:
    if key in {"enabled", "browser_notifications"}:
        return value.lower() in {"1", "true", "yes", "on"}
    if key == "cooldown_minutes":
        try:
            return max(1, min(1440, int(value)))
        except ValueError:
            return DEFAULT_ALERT_PREFERENCES[key]
    if value in {"LOW", "MEDIUM", "HIGH"}:
        return value
    return DEFAULT_ALERT_PREFERENCES[key]


async def get_alert_preferences(session: AsyncSession) -> dict[str, bool | int | str]:
    rows = (await session.scalars(select_settings())).all()
    preferences = dict(DEFAULT_ALERT_PREFERENCES)
    for row in rows:
        preference_key = ALERT_SETTING_KEYS.get(row.key)
        if preference_key is not None:
            preferences[preference_key] = _parse_value(preference_key, row.value)
    return preferences


def select_settings():
    """Keep the settings query in one place so alert reads stay easy to test."""

    from sqlalchemy import select

    return select(AppSetting).where(AppSetting.key.in_(ALERT_SETTING_KEYS))


async def update_alert_preferences(
    session: AsyncSession, updates: Mapping[str, bool | int | str]
) -> dict[str, bool | int | str]:
    reverse_keys = {value: key for key, value in ALERT_SETTING_KEYS.items()}
    for preference_key, value in updates.items():
        setting_key = reverse_keys.get(preference_key)
        if setting_key is None:
            continue
        row = await session.get(AppSetting, setting_key)
        if row is None:
            session.add(AppSetting(key=setting_key, value=str(value)))
        else:
            row.value = str(value)
    await session.commit()
    return await get_alert_preferences(session)
