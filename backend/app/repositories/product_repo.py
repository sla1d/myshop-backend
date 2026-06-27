"""Product repository."""
from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Repository for Product model with search/filter capabilities."""

    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def search(
        self,
        query: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        color: str | None = None,
        size: str | None = None,
        in_stock: bool | None = None,
        tenant_id: int | None = None,
    ) -> Sequence[Product]:
        stmt = select(Product)

        if tenant_id is not None:
            stmt = stmt.where(Product.tenant_id == tenant_id)

        if query:
            q = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(q),
                    Product.brand.ilike(q),
                    Product.category.ilike(q),
                )
            )
        if category:
            stmt = stmt.where(Product.category == category)
        if brand:
            stmt = stmt.where(Product.brand == brand)
        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        if color:
            stmt = stmt.where(Product.color == color)
        if size:
            stmt = stmt.where(Product.size == size)
        if in_stock:
            stmt = stmt.where(Product.in_stock == True)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_categories(self, tenant_id: int | None = None) -> list[str]:
        stmt = select(Product.category).distinct()
        if tenant_id is not None:
            stmt = stmt.where(Product.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return sorted([r[0] for r in result.all()])

    async def get_brands(self, tenant_id: int | None = None) -> list[str]:
        stmt = select(Product.brand).distinct()
        if tenant_id is not None:
            stmt = stmt.where(Product.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return sorted([r[0] for r in result.all() if r[0]])

    async def get_by_tenant(self, tenant_id: int) -> Sequence[Product]:
        return await self.get_all(filters={"tenant_id": tenant_id})
