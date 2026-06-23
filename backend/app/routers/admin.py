from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.database.connection import get_async_session
from app.models.order import Order
from app.models.product import Product
from app.models.promo import PromoCode
from app.models.user import User
from app.schemas.order import OrderAdmin, OrderItemAdmin
from app.schemas.product import Product as ProductSchema, ProductCreate, ProductUpdate
from app.schemas.user import UserResponse
from app.services.product import ProductService

router = APIRouter(prefix="/admin", tags=["Админ"])


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    status: str


# ─── Stats ───────────────────────────────────────────
@router.get("/stats")
async def get_stats(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    users_count = (await session.execute(select(func.count(User.id)))).scalar()
    products_count = (await session.execute(select(func.count(Product.id)))).scalar()
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar()
    revenue = (await session.execute(select(func.coalesce(func.sum(Order.total), 0)))).scalar()
    return {
        "total_users": users_count,
        "total_products": products_count,
        "total_orders": orders_count,
        "total_revenue": revenue,
    }


# ─── Users ───────────────────────────────────────────
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(User))
    return result.scalars().all()


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_role(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Роль: user или admin")
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.role = body.role
    await session.commit()
    await session.refresh(user)
    return user


# ─── Products ────────────────────────────────────────
@router.get("/products", response_model=list[ProductSchema])
async def admin_list_products(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Product))
    return result.scalars().all()


@router.post("/products", response_model=ProductSchema, status_code=201)
async def admin_create_product(
    body: ProductCreate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    product = Product(**body.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    svc = ProductService(session)
    await svc.invalidate()
    return product


@router.put("/products/{product_id}", response_model=ProductSchema)
async def admin_update_product(
    product_id: int,
    body: ProductUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await session.commit()
    await session.refresh(product)
    svc = ProductService(session)
    await svc.invalidate()
    return product


@router.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    await session.delete(product)
    await session.commit()
    svc = ProductService(session)
    await svc.invalidate()
    return {"detail": "Удалён"}


# ─── Orders ──────────────────────────────────────────
@router.get("/orders", response_model=list[OrderAdmin])
async def admin_list_orders(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Order).options(selectinload(Order.items).selectinload("product")).order_by(Order.id.desc())
    )
    orders = result.scalars().unique().all()
    out = []
    for o in orders:
        out.append(OrderAdmin(
            id=o.id,
            user_id=o.user_id,
            username=o.user.username,
            total=o.total,
            address=o.address,
            status=o.status,
            created_at=o.created_at.isoformat(),
            items=[OrderItemAdmin(
                product_name=i.product.name,
                quantity=i.quantity,
                price=i.price,
            ) for i in o.items],
        ))
    return out


@router.patch("/orders/{order_id}/status", response_model=OrderAdmin)
async def admin_change_order_status(
    order_id: int,
    body: StatusUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    valid = ("pending", "processing", "shipped", "delivered", "cancelled")
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Статус: {', '.join(valid)}")
    result = await session.execute(
        select(Order).options(selectinload(Order.items).selectinload("product")).where(Order.id == order_id)
    )
    order = result.scalars().unique().one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = body.status
    await session.commit()
    await session.refresh(order)
    return OrderAdmin(
        id=order.id,
        user_id=order.user_id,
        username=order.user.username,
        total=order.total,
        address=order.address,
        status=order.status,
        created_at=order.created_at.isoformat(),
        items=[OrderItemAdmin(
            product_name=i.product.name,
            quantity=i.quantity,
            price=i.price,
        ) for i in order.items],
    )


# ─── Promos ─────────────────────────────────────────
class PromoCreate(BaseModel):
    code: str
    discount_percent: int
    valid_until: str
    max_uses: int = 0


class PromoAdmin(BaseModel):
    id: int
    code: str
    discount_percent: int
    valid_until: str
    max_uses: int
    used_count: int
    active: bool


@router.get("/promos", response_model=list[PromoAdmin])
async def list_promos(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(PromoCode))
    return [
        PromoAdmin(
            id=p.id, code=p.code, discount_percent=p.discount_percent,
            valid_until=p.valid_until.isoformat(), max_uses=p.max_uses,
            used_count=p.used_count, active=p.active,
        )
        for p in result.scalars().all()
    ]


@router.post("/promos", response_model=PromoAdmin, status_code=201)
async def create_promo(
    body: PromoCreate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    promo = PromoCode(
        code=body.code.upper(),
        discount_percent=body.discount_percent,
        valid_until=datetime.fromisoformat(body.valid_until),
        max_uses=body.max_uses,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return PromoAdmin(
        id=promo.id, code=promo.code, discount_percent=promo.discount_percent,
        valid_until=promo.valid_until.isoformat(), max_uses=promo.max_uses,
        used_count=promo.used_count, active=promo.active,
    )


# ─── Celery Tasks ───────────────────────────────────
class TaskResponse(BaseModel):
    task_id: str
    status: str


@router.post("/tasks/report", response_model=TaskResponse)
async def trigger_report(
    admin: User = Depends(get_current_admin),
):
    """Запустить формирование отчёта (фоновая задача)."""
    from app.tasks import generate_sales_report
    task = generate_sales_report.delay()
    return TaskResponse(task_id=task.id, status="queued")


@router.post("/tasks/cleanup", response_model=TaskResponse)
async def trigger_cleanup(
    admin: User = Depends(get_current_admin),
):
    """Запустить очистку промокодов (фоновая задача)."""
    from app.tasks import cleanup_expired_promos
    task = cleanup_expired_promos.delay()
    return TaskResponse(task_id=task.id, status="queued")


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    admin: User = Depends(get_current_admin),
):
    """Проверить статус задачи."""
    from app.core.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
