from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.product import Product
from app.models.user import User
from app.models.wishlist import Wishlist
from app.schemas.wishlist import WishlistItem, WishlistResponse

router = APIRouter(prefix="/wishlist", tags=["Избранное"])


@router.get("", response_model=list[WishlistResponse])
async def get_wishlist(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить избранное текущего пользователя."""
    result = await session.execute(
        select(Wishlist, Product)
        .join(Product, Wishlist.product_id == Product.id)
        .where(Wishlist.user_id == user.id)
    )
    return [
        WishlistResponse(
            id=w.id,
            product_id=p.id,
            name=p.name,
            price=p.price,
            image=p.image,
            category=p.category,
            brand=p.brand,
            rating=p.rating,
        )
        for w, p in result.all()
    ]


@router.post("")
async def add_to_wishlist(
    body: WishlistItem,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Добавить товар в избранное."""
    product = await session.get(Product, body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    existing = await session.execute(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == body.product_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_exists"}

    item = Wishlist(user_id=user.id, product_id=body.product_id)
    session.add(item)
    await session.commit()
    return {"status": "ok"}


@router.delete("/{product_id}")
async def remove_from_wishlist(
    product_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить товар из избранного."""
    result = await session.execute(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == product_id)
    )
    item = result.scalar_one_or_none()
    if item:
        await session.delete(item)
        await session.commit()
    return {"status": "ok"}


@router.get("/check/{product_id}")
async def check_wishlist(
    product_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Проверить, в избранном ли товар."""
    result = await session.execute(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == product_id)
    )
    exists = result.scalar_one_or_none() is not None
    return {"is_wishlisted": exists}
