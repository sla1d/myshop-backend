"""Products API — public endpoints (read) + RBAC protected (write)."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.models.product import Product
from app.rbac.deps import RequirePermission
from app.schemas.product import Product as ProductSchema
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get("", response_model=list[ProductSchema])
async def get_products(
    search: str | None = Query(None),
    category: str | None = Query(None),
    brand: str | None = Query(None),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    min_rating: float | None = Query(None, ge=0, le=5),
    sort: str | None = Query(None),
    color: str | None = Query(None),
    size: str | None = Query(None),
    in_stock: bool | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    service = ProductService(session)
    return await service.get_all(
        search=search, category=category, brand=brand,
        min_price=min_price, max_price=max_price, min_rating=min_rating,
        sort=sort, color=color, size=size, in_stock=in_stock,
    )


@router.get("/categories", response_model=list[str])
async def get_categories(session: AsyncSession = Depends(get_async_session)):
    service = ProductService(session)
    return await service.get_categories()


@router.get("/brands", response_model=list[str])
async def get_brands(session: AsyncSession = Depends(get_async_session)):
    service = ProductService(session)
    return await service.get_brands()


@router.get("/colors", response_model=list[str])
async def get_colors(session: AsyncSession = Depends(get_async_session)):
    service = ProductService(session)
    return await service.get_colors()


@router.get("/sizes", response_model=list[str])
async def get_sizes(session: AsyncSession = Depends(get_async_session)):
    service = ProductService(session)
    return await service.get_sizes()


@router.get("/recommendations", response_model=list[ProductSchema])
async def get_recommendations(
    category: str | None = Query(None),
    limit: int = Query(6, ge=1, le=20),
    session: AsyncSession = Depends(get_async_session),
):
    service = ProductService(session)
    return await service.get_recommendations(category=category, limit=limit)


@router.get("/brand/{brand_name}", response_model=list[ProductSchema])
async def get_brand_products(
    brand_name: str,
    session: AsyncSession = Depends(get_async_session),
):
    service = ProductService(session)
    return await service.get_all(brand=brand_name)


@router.get("/export/csv")
async def export_products_csv(
    session: AsyncSession = Depends(get_async_session),
):
    service = ProductService(session)
    products = await service.get_all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Price", "Category", "Brand", "Rating", "Color", "Size", "In Stock"])
    for p in products:
        writer.writerow([p.id, p.name, p.price, p.category, p.brand, p.rating, p.color or '', p.size or '', p.in_stock])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, session: AsyncSession = Depends(get_async_session)):
    service = ProductService(session)
    product = await service.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product
