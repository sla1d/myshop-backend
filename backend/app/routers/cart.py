from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.cart import Cart
from app.models.product import Product
from app.models.user import User
from app.services.cart import CartService

router = APIRouter(prefix="/cart", tags=["Корзина"])


class CartItemRequest(BaseModel):
    product_id: int
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity >= 1")
        return v


@router.get("")
async def get_cart(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить корзину текущего пользователя."""
    service = CartService(session)
    items = await service.get_cart(user.id)
    total = sum(i["price"] * i["quantity"] for i in items)
    count = sum(i["quantity"] for i in items)
    return {"items": items, "total": total, "count": count}


@router.post("/add")
async def add_to_cart(
    body: CartItemRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Добавить товар в корзину (или увеличить количество)."""
    product = await session.get(Product, body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    service = CartService(session)
    await service.add_item(user.id, body.product_id, body.quantity)
    return {"status": "ok"}


@router.put("/item/{product_id}")
async def update_quantity(
    product_id: int,
    body: CartItemRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Установить точное количество товара."""
    service = CartService(session)
    await service.set_quantity(user.id, product_id, body.quantity)
    return {"status": "ok"}


@router.delete("/remove")
async def remove_from_cart(
    product_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить товар из корзины."""
    service = CartService(session)
    await service.remove_item(user.id, product_id)
    return {"status": "ok"}


@router.delete("/clear")
async def clear_cart(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Очистить корзину."""
    service = CartService(session)
    await service.clear(user.id)
    return {"status": "ok"}
