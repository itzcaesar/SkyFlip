from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import session_dependency, settings_dependency
from ..schemas import (
    AuctionListingsResponse,
    AuctionMarketResponse,
    AuctionStatusResponse,
)
from ..services.auction_collector import get_auction_status
from ..services.auction_valuation import list_auction_listings, list_auction_market

router = APIRouter(prefix="/auctions", tags=["auctions"])


@router.get("/status", response_model=AuctionStatusResponse, summary="Read Auction House freshness")
async def status(
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await get_auction_status(session, settings)


@router.get(
    "/market",
    response_model=AuctionMarketResponse,
    summary="List normalized Auction House comparables",
)
async def market(
    search: str = Query(default="", max_length=120),
    category: str = Query(default="", max_length=48),
    tier: str = Query(default="", max_length=24),
    sort_by: str = Query(default="discount", pattern="^(discount|price|listings|confidence)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await list_auction_market(
        session,
        settings,
        search=search,
        category=category,
        tier=tier,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/listings",
    response_model=AuctionListingsResponse,
    summary="List current Auction House BIN listings",
)
async def listings(
    search: str = Query(default="", max_length=120),
    item_key: str = Query(default="", max_length=200),
    category: str = Query(default="", max_length=48),
    tier: str = Query(default="", max_length=24),
    sort_by: str = Query(default="price", pattern="^(price|discount|ending)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
):
    return await list_auction_listings(
        session,
        settings,
        search=search,
        item_key=item_key,
        category=category,
        tier=tier,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
