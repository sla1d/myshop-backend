from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart
from app.models.product import Product
from app.models.user import User


class CartService:
    """Сервис для работы с корзиной."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_id(self, username: str) -> int | None:
        result = await self.session.execute(select(User.id).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_cart(self, user_id: int) -> list[dict]:
        result = await self.session.execute(
            select(Cart, Product)
            .join(Product, Cart.product_id == Product.id)
            .where(Cart.user_id == user_id, Cart.product_id > 0)
        )
        rows = result.all()
        return [
            {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "image": product.image,
                "quantity": cart.quantity,
            }
            for cart, product in rows
        ]

    async def add_item(self, user_id: int, product_id: int, quantity: int) -> None:
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.quantity += quantity
        else:
            self.session.add(Cart(user_id=user_id, product_id=product_id, quantity=quantity))

        await self.session.commit()

    async def set_quantity(self, user_id: int, product_id: int, quantity: int) -> None:
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
        )
        item = result.scalar_one_or_none()
        if item:
            item.quantity = quantity
            await self.session.commit()

    async def remove_item(self, user_id: int, product_id: int) -> None:
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
        )
        item = result.scalar_one_or_none()
        if item:
            await self.session.delete(item)
            await self.session.commit()

    async def clear(self, user_id: int) -> None:
        result = await self.session.execute(select(Cart).where(Cart.user_id == user_id))
        for item in result.scalars().all():
            await self.session.delete(item)
        await self.session.commit()
