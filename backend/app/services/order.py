from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.promo import PromoCode


class OrderService:
    """Сервис для работы с заказами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, address: str, promo_code: str | None = None) -> dict:
        """Создать заказ из корзины пользователя с опциональным промокодом."""
        result = await self.session.execute(
            select(Cart, Product)
            .join(Product, Cart.product_id == Product.id)
            .where(Cart.user_id == user_id, Cart.product_id > 0)
        )
        cart_rows = result.all()

        if not cart_rows:
            raise ValueError("Корзина пуста")

        total = sum(product.price * cart.quantity for cart, product in cart_rows)
        discount = 0

        if promo_code:
            promo_result = await self.session.execute(
                select(PromoCode).where(PromoCode.code == promo_code.upper())
            )
            promo = promo_result.scalar_one_or_none()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if promo and promo.active and promo.valid_until.replace(tzinfo=None) >= now:
                if promo.max_uses == 0 or promo.used_count < promo.max_uses:
                    discount = total * promo.discount_percent // 100
                    promo.used_count += 1

        final_total = total - discount

        order = Order(
            user_id=user_id,
            total=final_total,
            address=address,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(order)
        await self.session.flush()

        for cart, product in cart_rows:
            self.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=cart.quantity,
                    price=product.price,
                )
            )

        carts_result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        for cart_item in carts_result.scalars().all():
            await self.session.delete(cart_item)

        await self.session.commit()

        return {"order_id": order.id, "total": final_total, "discount": discount}
