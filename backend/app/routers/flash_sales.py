import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.flash_sale import FlashSale
from app.models.product import Product

router = APIRouter(prefix="/flash-sales", tags=["Flash Sales"])
logger = logging.getLogger(__name__)


class FlashSaleCreate(BaseModel):
    product_id: int
    discount_percent: int
    start_at: str
    end_at: str


class FlashSaleResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    original_price: int
    sale_price: int
    discount_percent: int
    start_at: str
    end_at: str
    active: bool
    ends_in_seconds: int


@router.get("/active", response_model=list[FlashSaleResponse])
async def get_active_flash_sales(
    session: AsyncSession = Depends(get_async_session),
):
    """Получить активные flash sales."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(FlashSale, Product)
        .join(Product, FlashSale.product_id == Product.id)
        .where(FlashSale.active == True, FlashSale.start_at <= now, FlashSale.end_at > now)
    )
    rows = result.all()
    responses = []
    for sale, product in rows:
        sale_price = int(product.price * (100 - sale.discount_percent) / 100)
        ends_in = int((sale.end_at - now).total_seconds())
        responses.append(FlashSaleResponse(
            id=sale.id,
            product_id=product.id,
            product_name=product.name,
            original_price=product.price,
            sale_price=sale_price,
            discount_percent=sale.discount_percent,
            start_at=sale.start_at.isoformat(),
            end_at=sale.end_at.isoformat(),
            active=sale.active,
            ends_in_seconds=max(0, ends_in),
        ))
    return responses


@router.post("/create")
async def create_flash_sale(
    body: FlashSaleCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Создать flash sale (admin)."""
    from datetime import datetime as dt
    sale = FlashSale(
        product_id=body.product_id,
        discount_percent=body.discount_percent,
        start_at=dt.fromisoformat(body.start_at),
        end_at=dt.fromisoformat(body.end_at),
        active=True,
    )
    session.add(sale)
    await session.commit()
    logger.info("Flash sale created: product=%d, discount=%d%%", body.product_id, body.discount_percent)
    return {"status": "ok", "id": sale.id}
