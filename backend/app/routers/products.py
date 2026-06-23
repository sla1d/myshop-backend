from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.schemas.product import Product
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get("", response_model=list[Product])
async def get_products(
    search: str | None = Query(None, description="Поиск по названию"),
    category: str | None = Query(None, description="Фильтр по категории"),
    brand: str | None = Query(None, description="Фильтр по бренду"),
    min_price: int | None = Query(None, ge=0, description="Минимальная цена"),
    max_price: int | None = Query(None, ge=0, description="Максимальная цена"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Минимальный рейтинг"),
    sort: str | None = Query(None, description="Сортировка: price_asc, price_desc, rating, name, newest"),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить список товаров с поиском, фильтрами и сортировкой."""
    service = ProductService(session)
    return await service.get_all(
        search=search, category=category, brand=brand,
        min_price=min_price, max_price=max_price, min_rating=min_rating,
        sort=sort,
    )


@router.get("/categories", response_model=list[str])
async def get_categories(session: AsyncSession = Depends(get_async_session)):
    """Получить список категорий."""
    service = ProductService(session)
    return await service.get_categories()


@router.get("/brands", response_model=list[str])
async def get_brands(session: AsyncSession = Depends(get_async_session)):
    """Получить список брендов."""
    service = ProductService(session)
    return await service.get_brands()


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int, session: AsyncSession = Depends(get_async_session)):
    """Получить товар по ID."""
    service = ProductService(session)
    product = await service.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product
