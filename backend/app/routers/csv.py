"""CSV Import/Export API — bulk product management."""
import csv
import io
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.product import Product
from app.models.user import User
from app.rbac.deps import RequirePermission
from app.services.product import ProductService

router = APIRouter(prefix="/products/csv", tags=["CSV"])
logger = logging.getLogger("myshop.csv")


class CSVImportResult(BaseModel):
    total_rows: int
    imported: int
    updated: int
    errors: list[str]


class ProductCSVRow(BaseModel):
    id: int | None = None
    name: str
    price: int
    category: str = ""
    brand: str = ""
    rating: float = 0.0
    color: str = ""
    size: str = ""
    image: str = ""
    in_stock: bool = True
    stock_quantity: int = 0
    description: str = ""


CSV_COLUMNS = [
    "id", "name", "price", "category", "brand", "rating",
    "color", "size", "image", "in_stock", "stock_quantity", "description",
]


# ─── Export CSV ──────────────────────────────────────
@router.get("/export")
async def export_products_csv(
    request: Request,
    user: User = Depends(RequirePermission("analytics.export")),
    session: AsyncSession = Depends(get_async_session),
):
    """Export all products to CSV."""
    tenant_id = getattr(request.state, "tenant_id", None)
    from sqlalchemy import select
    stmt = select(Product)
    if tenant_id:
        stmt = stmt.where(Product.tenant_id == tenant_id)
    result = await session.execute(stmt)
    products = result.scalars().all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()

    for p in products:
        writer.writerow({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "category": p.category or "",
            "brand": p.brand or "",
            "rating": p.rating or 0,
            "color": getattr(p, "color", "") or "",
            "size": getattr(p, "size", "") or "",
            "image": getattr(p, "image", "") or "",
            "in_stock": getattr(p, "in_stock", True),
            "stock_quantity": getattr(p, "stock_quantity", 0),
            "description": getattr(p, "description", "") or "",
        })

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=products_{tenant_id or 'all'}.csv"
        },
    )


# ─── Import CSV ──────────────────────────────────────
@router.post("/import", response_model=CSVImportResult)
async def import_products_csv(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(RequirePermission("product.create")),
    session: AsyncSession = Depends(get_async_session),
):
    """Import products from CSV file.

    CSV format: name,price,category,brand,rating,color,size,image,in_stock,stock_quantity,description
    - If id is provided and exists → update product
    - If id is missing or not found → create new product
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Файл должен быть .csv")

    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))

    tenant_id = getattr(request.state, "tenant_id", None)
    imported = 0
    updated = 0
    errors = []
    total_rows = 0

    svc = ProductService(session)

    for row_num, row in enumerate(reader, start=2):
        total_rows += 1
        try:
            name = row.get("name", "").strip()
            if not name:
                errors.append(f"Строка {row_num}: пустое имя")
                continue

            price = int(float(row.get("price", 0)))
            if price <= 0:
                errors.append(f"Строка {row_num}: цена должна быть > 0")
                continue

            product_id = row.get("id", "").strip()
            in_stock_str = row.get("in_stock", "true").strip().lower()
            in_stock = in_stock_str in ("true", "1", "yes", "да")

            product_data = {
                "name": name,
                "price": price,
                "category": row.get("category", "").strip(),
                "brand": row.get("brand", "").strip(),
                "rating": float(row.get("rating", 0) or 0),
                "color": row.get("color", "").strip() or None,
                "size": row.get("size", "").strip() or None,
                "image": row.get("image", "").strip() or "",
                "in_stock": in_stock,
                "stock_quantity": int(row.get("stock_quantity", 0) or 0),
                "description": row.get("description", "").strip() or None,
            }

            if product_id and product_id.isdigit():
                # Try to update existing product
                existing = await session.get(Product, int(product_id))
                if existing and (not tenant_id or existing.tenant_id == tenant_id):
                    for key, value in product_data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    updated += 1
                    continue

            # Create new product
            product = Product(**product_data, tenant_id=tenant_id)
            session.add(product)
            imported += 1

        except Exception as e:
            errors.append(f"Строка {row_num}: {str(e)}")

    await session.commit()
    await svc.invalidate()

    logger.info(
        "CSV import: total=%d, imported=%d, updated=%d, errors=%d",
        total_rows, imported, updated, len(errors),
    )

    return CSVImportResult(
        total_rows=total_rows,
        imported=imported,
        updated=updated,
        errors=errors,
    )


# ─── Download CSV template ──────────────────────────
@router.get("/template")
async def download_csv_template():
    """Download a CSV template for import."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerow({
        "name": "Смартфон X",
        "price": 29999,
        "category": "electronics",
        "brand": "TechCo",
        "rating": 4.5,
        "color": "black",
        "size": "standard",
        "image": "https://example.com/photo.jpg",
        "in_stock": True,
        "stock_quantity": 50,
        "description": "Отличный смартфон",
    })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_template.csv"},
    )
