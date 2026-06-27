import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, cache_get, cache_set
from app.models.product import Product

logger = logging.getLogger("myshop.products")

SORT_MAP = {
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "rating": Product.rating.desc(),
    "name": Product.name.asc(),
    "newest": Product.id.desc(),
}


class ProductService:
    """Сервис для работы с товарами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _build_cache_key(self, **kwargs) -> str:
        parts = []
        for k, v in sorted(kwargs.items()):
            if v is not None:
                parts.append(f"{k}={v}")
        return "products:" + ("|".join(parts) if parts else "all")

    async def get_all(
        self,
        search: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        min_rating: float | None = None,
        sort: str | None = None,
        color: str | None = None,
        size: str | None = None,
        in_stock: bool | None = None,
    ) -> list[Product]:
        cache_key = self._build_cache_key(
            search=search, category=category, brand=brand,
            min_price=min_price, max_price=max_price,
            min_rating=min_rating, sort=sort,
            color=color, size=size, in_stock=in_stock,
        )
        cached = await cache_get(cache_key)
        if cached is not None:
            return [Product(**p) for p in cached]

        stmt = select(Product)
        if search:
            from sqlalchemy import or_
            q = f"%{search}%"
            # Умный поиск: exact match, then contains, then LIKE
            stmt = stmt.where(
                or_(
                    Product.name.ilike(q),
                    Product.brand.ilike(q),
                    Product.category.ilike(q),
                    Product.name.ilike(f"%{'%'.join(search)}%"),
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
        if min_rating is not None:
            stmt = stmt.where(Product.rating >= min_rating)
        if color:
            stmt = stmt.where(Product.color == color)
        if size:
            stmt = stmt.where(Product.size == size)
        if in_stock:
            stmt = stmt.where(Product.in_stock == True)
        if sort and sort in SORT_MAP:
            stmt = stmt.order_by(SORT_MAP[sort])
        result = await self.session.execute(stmt)
        products = list(result.scalars().all())

        await cache_set(cache_key, [
            {"id": p.id, "name": p.name, "price": p.price, "image": p.image,
             "category": p.category, "brand": p.brand, "rating": p.rating,
             "color": p.color, "size": p.size, "in_stock": p.in_stock,
             "stock_quantity": p.stock_quantity}
            for p in products
        ])
        return products

    async def get_categories(self) -> list[str]:
        cached = await cache_get("products:categories")
        if cached is not None:
            return cached

        result = await self.session.execute(select(Product.category).distinct())
        cats = sorted([r[0] for r in result.all()])
        await cache_set("products:categories", cats)
        return cats

    async def get_brands(self) -> list[str]:
        cached = await cache_get("products:brands")
        if cached is not None:
            return cached

        result = await self.session.execute(select(Product.brand).distinct())
        brands = sorted([r[0] for r in result.all() if r[0]])
        await cache_set("products:brands", brands)
        return brands

    async def get_by_id(self, product_id: int) -> Product | None:
        cached = await cache_get(f"product:{product_id}")
        if cached is not None:
            return Product(**cached)

        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product:
            await cache_set(f"product:{product_id}", {
                "id": product.id, "name": product.name, "price": product.price,
                "image": product.image, "category": product.category,
                "brand": product.brand, "rating": product.rating,
                "color": product.color, "size": product.size,
                "in_stock": product.in_stock, "stock_quantity": product.stock_quantity,
            })
        return product

    async def get_by_category(self, category: str) -> list[Product]:
        return await self.get_all(category=category)

    async def get_recommendations(self, category: str | None = None, limit: int = 6) -> list[Product]:
        if category:
            products = await self.get_all(category=category, sort="rating")
            return products[:limit]
        products = await self.get_all(sort="rating")
        return products[:limit]

    async def get_colors(self) -> list[str]:
        result = await self.session.execute(select(Product.color).distinct())
        return sorted([r[0] for r in result.all() if r[0]])

    async def get_sizes(self) -> list[str]:
        result = await self.session.execute(select(Product.size).distinct())
        return sorted([r[0] for r in result.all() if r[0]])

    async def invalidate(self) -> None:
        """Очистить весь кэш товаров."""
        await cache_delete("products:*")
        await cache_delete("product:*")
