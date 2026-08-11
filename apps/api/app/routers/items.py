from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import session_dependency
from ..models import BazaarProduct

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/search", summary="Search observed normalized items")
async def search_items(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(session_dependency),
):
    products = (
        await session.scalars(
            select(BazaarProduct)
            .where(
                BazaarProduct.is_active.is_(True),
                (BazaarProduct.product_id.ilike(f"%{q.strip()}%"))
                | (BazaarProduct.display_name.ilike(f"%{q.strip()}%")),
            )
            .order_by(asc(BazaarProduct.display_name))
            .limit(limit)
        )
    ).all()
    return {
        "items": [
            {"id": product.product_id, "name": product.display_name, "market": "bazaar"}
            for product in products
        ]
    }
