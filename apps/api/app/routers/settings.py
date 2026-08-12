from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import session_dependency, settings_dependency
from ..schemas import MarketSettingsResponse, MarketSettingsUpdate
from ..services.preferences import (
    market_settings_response,
    reset_market_settings,
    update_market_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=MarketSettingsResponse, summary="Read local market settings")
async def get_settings(
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await market_settings_response(session, settings)


@router.patch("", response_model=MarketSettingsResponse, summary="Update local market settings")
async def patch_settings(
    payload: MarketSettingsUpdate,
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await update_market_settings(
        session, settings, payload.model_dump(exclude_none=True)
    )


@router.delete("", response_model=MarketSettingsResponse, summary="Reset local market settings")
async def delete_settings(
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await reset_market_settings(session, settings)
