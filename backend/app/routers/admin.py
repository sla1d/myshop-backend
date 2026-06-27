"""Admin API — RBAC protected endpoints."""
import csv
import io
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_tenant_id_from_request
from app.database.connection import get_async_session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.promo import PromoCode
from app.models.user import User
from app.rbac.deps import RequirePermission
from app.schemas.order import OrderAdmin, OrderItemAdmin
from app.schemas.product import Product as ProductSchema, ProductCreate, ProductUpdate
from app.schemas.user import UserResponse
from app.security.audit import audit_price_change, audit_product_delete, audit_role_change
from app.services.product import ProductService

router = APIRouter(prefix="/admin", tags=["Админ"])
logger = logging.getLogger("myshop.admin")


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    status: str


# ─── Stats ───────────────────────────────────────────
@router.get("/stats")
async def get_stats(
    request: Request,
    user: User = Depends(RequirePermission("analytics.view")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = select(func.count(User.id))
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    users_count = (await session.execute(stmt)).scalar()

    stmt = select(func.count(Product.id))
    if tenant_id:
        stmt = stmt.where(Product.tenant_id == tenant_id)
    products_count = (await session.execute(stmt)).scalar()

    stmt = select(func.count(Order.id))
    if tenant_id:
        stmt = stmt.where(Order.tenant_id == tenant_id)
    orders_count = (await session.execute(stmt)).scalar()

    stmt = select(func.coalesce(func.sum(Order.total), 0))
    if tenant_id:
        stmt = stmt.where(Order.tenant_id == tenant_id)
    revenue = (await session.execute(stmt)).scalar()

    return {
        "total_users": users_count,
        "total_products": products_count,
        "total_orders": orders_count,
        "total_revenue": revenue,
    }


# ─── Users ───────────────────────────────────────────
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    user: User = Depends(RequirePermission("user.invite")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = select(User)
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_role(
    user_id: int,
    body: RoleUpdate,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Роль: user или admin")
    target_user = await session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    old_role = target_user.role
    target_user.role = body.role
    await session.commit()
    await session.refresh(target_user)

    # Audit log
    tenant_id = getattr(request.state, "tenant_id", None)
    ip = request.client.host if request.client else None
    await audit_role_change(
        session, tenant_id, user.id, user.username,
        user_id, old_role, body.role,
    )

    return target_user


# ─── RBAC Roles ──────────────────────────────────────
class RBACRoleAssign(BaseModel):
    role_name: str


@router.get("/roles")
async def list_roles(
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import Role, RolePermission, Permission
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permissions": [p.name for p in r.permissions],
        }
        for r in roles
    ]


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import UserRole, Role
    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    target_user = await session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    stmt = (
        select(UserRole)
        .options(selectinload(UserRole.role))
        .where(UserRole.user_id == user_id)
    )
    if tenant_id:
        stmt = stmt.where(UserRole.tenant_id == tenant_id)
    result = await session.execute(stmt)
    user_roles = result.scalars().all()
    return [
        {"role_name": ur.role.name, "description": ur.role.description, "assigned_at": ur.assigned_at.isoformat()}
        for ur in user_roles
    ]


@router.post("/users/{user_id}/roles", status_code=201)
async def assign_role(
    user_id: int,
    body: RBACRoleAssign,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import UserRole, Role
    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant не определён")

    if body.role_name == "owner":
        owner_check = await session.execute(
            select(UserRole).join(Role).where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == tenant_id,
                Role.name == "owner",
            )
        )
        if not owner_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Только владелец может назначать роль владельца")

    target_user = await session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    role_result = await session.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail=f"Роль '{body.role_name}' не найдена")

    existing = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            UserRole.role_id == role.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Роль '{body.role_name}' уже назначена")

    user_role = UserRole(
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role.id,
        assigned_by=user.id,
    )
    session.add(user_role)
    await session.commit()

    from app.security.audit import AuditService
    audit = AuditService(session)
    await audit.log(action="role_assigned", tenant_id=tenant_id, user_id=user.id, username=user.username, entity="user_role", entity_id=user_id, details={"role": body.role_name, "expires_days": None})
    await session.commit()

    logger.info("Role assigned: user=%d, role=%s, tenant=%d", user_id, body.role_name, tenant_id)
    return {"detail": f"Роль '{body.role_name}' назначена пользователю {target_user.username}"}


@router.delete("/users/{user_id}/roles/{role_name}")
async def revoke_role(
    user_id: int,
    role_name: str,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import UserRole, Role
    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant не определён")

    if role_name == "owner":
        owner_check = await session.execute(
            select(UserRole).join(Role).where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == tenant_id,
                Role.name == "owner",
            )
        )
        if not owner_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Только владелец может снять роль владельца")
        if user_id == user.id:
            raise HTTPException(status_code=403, detail="Нельзя снять роль владельца у самого себя")

    role_result = await session.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail=f"Роль '{role_name}' не найдена")

    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            UserRole.role_id == role.id,
        )
    )
    user_role = result.scalar_one_or_none()
    if not user_role:
        raise HTTPException(status_code=404, detail=f"Роль '{role_name}' не назначена этому пользователю")

    await session.delete(user_role)
    await session.commit()

    from app.security.audit import AuditService
    audit = AuditService(session)
    await audit.log(action="role_removed", tenant_id=tenant_id, user_id=user.id, username=user.username, entity="user_role", entity_id=user_id, details={"role": role_name})
    await session.commit()

    logger.info("Role revoked: user=%d, role=%s, tenant=%d", user_id, role_name, tenant_id)
    return {"detail": f"Роль '{role_name}' снята"}


# ─── Products ────────────────────────────────────────
@router.get("/products", response_model=list[ProductSchema])
async def admin_list_products(
    request: Request,
    user: User = Depends(RequirePermission("product.view")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = select(Product)
    if tenant_id:
        stmt = stmt.where(Product.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/products", response_model=ProductSchema, status_code=201)
async def admin_create_product(
    body: ProductCreate,
    request: Request,
    user: User = Depends(RequirePermission("product.create")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    product = Product(**body.model_dump(), tenant_id=tenant_id)
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
    request: Request,
    user: User = Depends(RequirePermission("product.update")),
    session: AsyncSession = Depends(get_async_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Track price change for audit
    old_price = product.price
    new_data = body.model_dump(exclude_unset=True)

    for field, value in new_data.items():
        setattr(product, field, value)
    await session.commit()
    await session.refresh(product)

    # Audit price change
    if "price" in new_data and new_data["price"] != old_price:
        tenant_id = getattr(request.state, "tenant_id", None)
        await audit_price_change(
            session, tenant_id, user.id, user.username,
            product_id, old_price, product.price,
        )

    svc = ProductService(session)
    await svc.invalidate()
    return product


@router.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: int,
    request: Request,
    user: User = Depends(RequirePermission("product.delete")),
    session: AsyncSession = Depends(get_async_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Audit before delete
    tenant_id = getattr(request.state, "tenant_id", None)
    await audit_product_delete(session, tenant_id, user.id, user.username, product_id)

    await session.delete(product)
    await session.commit()
    svc = ProductService(session)
    await svc.invalidate()
    return {"detail": "Удалён"}


# ─── Orders ──────────────────────────────────────────
@router.get("/orders", response_model=list[OrderAdmin])
async def admin_list_orders(
    request: Request,
    user: User = Depends(RequirePermission("order.view")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = (
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.id.desc())
    )
    if tenant_id:
        stmt = stmt.where(Order.tenant_id == tenant_id)
    result = await session.execute(stmt)
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
    request: Request,
    user: User = Depends(RequirePermission("order.update")),
    session: AsyncSession = Depends(get_async_session),
):
    valid = ("pending", "processing", "shipped", "delivered", "cancelled")
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Статус: {', '.join(valid)}")
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
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
    request: Request,
    user: User = Depends(RequirePermission("promo.view")),
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
    request: Request,
    user: User = Depends(RequirePermission("promo.create")),
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

    # Audit
    tenant_id = getattr(request.state, "tenant_id", None)
    from app.security.audit import audit_discount_create
    await audit_discount_create(session, tenant_id, user.id, user.username, promo.code, promo.discount_percent)

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
    user: User = Depends(RequirePermission("analytics.view")),
):
    from app.tasks import generate_sales_report
    task = generate_sales_report.delay(tenant_id=0)
    return TaskResponse(task_id=task.id, status="queued")


@router.post("/tasks/cleanup", response_model=TaskResponse)
async def trigger_cleanup(
    user: User = Depends(RequirePermission("tenant.manage")),
):
    from app.tasks import cleanup_expired_promos
    task = cleanup_expired_promos.delay()
    return TaskResponse(task_id=task.id, status="queued")


# ─── CSV Export ──────────────────────────────────────
@router.get("/export/products")
async def export_products(
    request: Request,
    user: User = Depends(RequirePermission("analytics.export")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = select(Product)
    if tenant_id:
        stmt = stmt.where(Product.tenant_id == tenant_id)
    result = await session.execute(stmt)
    products = result.scalars().all()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Name", "Price", "Category", "Brand", "Rating"])
    for p in products:
        w.writerow([p.id, p.name, p.price, p.category, p.brand, p.rating])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=products.csv"})


@router.get("/export/orders")
async def export_orders(
    request: Request,
    user: User = Depends(RequirePermission("analytics.export")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
    if tenant_id:
        stmt = stmt.where(Order.tenant_id == tenant_id)
    result = await session.execute(stmt)
    orders = result.scalars().unique().all()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Order ID", "User", "Total", "Status", "Address", "Created"])
    for o in orders:
        w.writerow([o.id, o.user_id, o.total, o.status, o.address, o.created_at.isoformat()])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=orders.csv"})


@router.get("/export/users")
async def export_users(
    request: Request,
    user: User = Depends(RequirePermission("user.invite")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    stmt = select(User)
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    result = await session.execute(stmt)
    users = result.scalars().all()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Username", "Email", "Role", "Full Name"])
    for u in users:
        w.writerow([u.id, u.username, u.email, u.role, u.full_name])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=users.csv"})


# ─── RBAC: Custom Roles CRUD ─────────────────────────
class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permission_names: list[str] = []


class RoleUpdateBody(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_names: list[str] | None = None


@router.get("/roles/full")
async def get_roles_full(
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import Role, RolePermission, Permission
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "description": r.description,
            "is_system": r.is_system,
            "permissions": [{"name": p.name, "description": p.description, "category": p.category} for p in r.permissions],
        }
        for r in roles
    ]


@router.post("/roles")
async def create_custom_role(
    body: RoleCreate,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import Role, RolePermission, Permission
    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id

    existing = await session.execute(select(Role).where(Role.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Роль '{body.name}' уже существует")

    if body.name in ("owner", "superadmin"):
        raise HTTPException(status_code=403, detail="Нельзя создавать роль с именем owner или superadmin")

    from app.models.license import Tenant, PLANS
    tenant = await session.get(Tenant, tenant_id)
    if tenant:
        plan_key = tenant.plan if tenant.plan in PLANS else "starter"
        max_roles = PLANS[plan_key].get("max_admins", 5)
        if max_roles != -1:
            role_count_result = await session.execute(select(func.count(Role.id)).where(Role.is_system == False))
            custom_count = role_count_result.scalar() or 0
            if custom_count >= max_roles:
                raise HTTPException(status_code=403, detail=f"Лимит кастомных ролей ({max_roles}) для тарифа {plan_key}")

    role = Role(name=body.name, description=body.description, is_system=False)
    session.add(role)
    await session.flush()

    for perm_name in body.permission_names:
        perm_result = await session.execute(select(Permission).where(Permission.name == perm_name))
        perm = perm_result.scalar_one_or_none()
        if perm:
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await session.commit()
    logger.info("Custom role created: %s by user=%d", body.name, user.id)
    return {"detail": f"Роль '{body.name}' создана", "role_id": role.id}


@router.put("/roles/{role_id}")
async def update_custom_role(
    role_id: int,
    body: RoleUpdateBody,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import Role, RolePermission, Permission
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Нельзя изменять системные роли")
    if role.name in ("owner", "superadmin"):
        raise HTTPException(status_code=403, detail="Нельзя изменять роль owner/superadmin")

    if body.name is not None:
        dup = await session.execute(select(Role).where(Role.name == body.name, Role.id != role_id))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Роль '{body.name}' уже существует")
        role.name = body.name
    if body.description is not None:
        role.description = body.description

    if body.permission_names is not None:
        await session.execute(
            RolePermission.__table__.delete().where(RolePermission.role_id == role_id)
        )
        for perm_name in body.permission_names:
            perm_result = await session.execute(select(Permission).where(Permission.name == perm_name))
            perm = perm_result.scalar_one_or_none()
            if perm:
                session.add(RolePermission(role_id=role_id, permission_id=perm.id))

    await session.commit()
    logger.info("Custom role updated: id=%d by user=%d", role_id, user.id)
    return {"detail": f"Роль обновлена"}


@router.delete("/roles/{role_id}")
async def delete_custom_role(
    role_id: int,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import Role, RolePermission, UserRole
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Нельзя удалять системные роли")

    assigned = await session.execute(select(func.count(UserRole.id)).where(UserRole.role_id == role_id))
    if assigned.scalar() > 0:
        raise HTTPException(status_code=409, detail="Нельзя удалить роль — она назначена пользователям. Сначала снимите её.")

    await session.execute(RolePermission.__table__.delete().where(RolePermission.role_id == role_id))
    await session.delete(role)
    await session.commit()
    logger.info("Custom role deleted: id=%d by user=%d", role_id, user.id)
    return {"detail": "Роль удалена"}


# ─── RBAC: Permission Matrix ──────────────────────────
@router.get("/permissions/matrix")
async def get_permission_matrix(
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import Role, Permission, RolePermission
    roles_result = await session.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = roles_result.scalars().all()
    perms_result = await session.execute(select(Permission))
    all_perms = perms_result.scalars().all()

    perm_categories = {}
    for p in all_perms:
        cat = p.category or "other"
        if cat not in perm_categories:
            perm_categories[cat] = []
        perm_categories[cat].append({"name": p.name, "description": p.description or p.name})

    matrix = {}
    for r in roles:
        matrix[r.id] = [p.name for p in r.permissions]

    return {
        "roles": [{"id": r.id, "name": r.name, "description": r.description, "is_system": r.is_system} for r in roles],
        "permissions": perm_categories,
        "matrix": matrix,
    }


# ─── RBAC: Bulk Assign ────────────────────────────────
class BulkAssign(BaseModel):
    user_ids: list[int]
    role_name: str
    expires_days: int | None = None


@router.post("/roles/bulk-assign")
async def bulk_assign_roles(
    body: BulkAssign,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import UserRole, Role
    from datetime import timedelta

    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant не определён")

    role_result = await session.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail=f"Роль '{body.role_name}' не найдена")

    expires_at = None
    if body.expires_days and body.expires_days > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_days)

    assigned = 0
    skipped = 0
    for uid in body.user_ids:
        target = await session.get(User, uid)
        if not target:
            skipped += 1
            continue
        existing = await session.execute(
            select(UserRole).where(
                UserRole.user_id == uid,
                UserRole.tenant_id == tenant_id,
                UserRole.role_id == role.id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        session.add(UserRole(
            user_id=uid, tenant_id=tenant_id, role_id=role.id,
            assigned_by=user.id, expires_at=expires_at,
        ))
        assigned += 1

    await session.commit()
    if assigned > 0:
        from app.security.audit import AuditService
        audit = AuditService(session)
        await audit.log(action="role_assigned", tenant_id=tenant_id, user_id=user.id, username=user.username, entity="bulk", entity_id=None, details={"role": body.role_name, "count": assigned, "user_ids": body.user_ids[:10]})
        await session.commit()
    logger.info("Bulk assign: role=%s, assigned=%d, skipped=%d by user=%d", body.role_name, assigned, skipped, user.id)
    return {"detail": f"Назначено: {assigned}, пропущено: {skipped}", "assigned": assigned, "skipped": skipped}


# ─── RBAC: Assignment History ─────────────────────────
@router.get("/roles/history")
async def get_role_history(
    limit: int = 50,
    user: User = Depends(RequirePermission("audit.view")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.security.models import AuditLog
    from app.rbac.models import UserRole, Role

    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.action.in_(["role_assigned", "role_removed", "user.role_change"]))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "details": json.dumps(log.details) if log.details else (log.details or ""),
            "user_id": log.user_id,
            "username": log.username or "",
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ─── RBAC: Default Role for Tenant ────────────────────
class DefaultRoleUpdate(BaseModel):
    role_name: str | None = None


@router.patch("/tenant/default-role")
async def set_default_role(
    body: DefaultRoleUpdate,
    request: Request,
    user: User = Depends(RequirePermission("tenant.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.models.license import Tenant
    from app.rbac.models import Role

    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant не определён")

    if body.role_name:
        role_check = await session.execute(select(Role).where(Role.name == body.role_name))
        if not role_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Роль '{body.role_name}' не найдена")

    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant не найден")
    tenant.default_role = body.role_name
    await session.commit()
    return {"detail": f"Роль по умолчанию: {body.role_name or 'не задана'}"}


# ─── RBAC: Admin count for plan ───────────────────────
@router.get("/roles/limits")
async def get_role_limits(
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.models.license import Tenant, PLANS
    from app.rbac.models import Role

    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    tenant = await session.get(Tenant, tenant_id) if tenant_id else None
    plan_key = tenant.plan if tenant and tenant.plan in PLANS else "starter"
    plan = PLANS.get(plan_key, PLANS["starter"])

    custom_count_result = await session.execute(select(func.count(Role.id)).where(Role.is_system == False))
    custom_count = custom_count_result.scalar() or 0
    max_custom = plan.get("max_admins", 5)

    return {
        "plan": plan_key,
        "max_custom_roles": max_custom,
        "current_custom_roles": custom_count,
    }


# ─── Assign temporary role (with expiry) ──────────────
class TempRoleAssign(BaseModel):
    role_name: str
    expires_days: int


@router.post("/users/{user_id}/roles/temp")
async def assign_temporary_role(
    user_id: int,
    body: TempRoleAssign,
    request: Request,
    user: User = Depends(RequirePermission("user.assign_role")),
    session: AsyncSession = Depends(get_async_session),
):
    from app.rbac.models import UserRole, Role
    from datetime import timedelta

    tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant не определён")

    if body.expires_days < 1 or body.expires_days > 365:
        raise HTTPException(status_code=400, detail="Срок от 1 до 365 дней")

    target_user = await session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    role_result = await session.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail=f"Роль '{body.role_name}' не найдена")

    existing = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            UserRole.role_id == role.id,
        )
    )
    existing_ur = existing.scalar_one_or_none()
    if existing_ur:
        existing_ur.expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_days)
        await session.commit()
        return {"detail": f"Роль '{body.role_name}' продлена до {(datetime.now(timezone.utc) + timedelta(days=body.expires_days)).strftime('%d.%m.%Y')}"}

    expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_days)
    session.add(UserRole(
        user_id=user_id, tenant_id=tenant_id, role_id=role.id,
        assigned_by=user.id, expires_at=expires_at,
    ))
    await session.commit()
    from app.security.audit import AuditService
    audit = AuditService(session)
    await audit.log(action="role_assigned", tenant_id=tenant_id, user_id=user.id, username=user.username, entity="user_role", entity_id=user_id, details={"role": body.role_name, "expires_days": body.expires_days})
    await session.commit()
    logger.info("Temp role assigned: user=%d, role=%s, days=%d by user=%d", user_id, body.role_name, body.expires_days, user.id)
    return {"detail": f"Роль '{body.role_name}' назначена на {body.expires_days} дней (до {expires_at.strftime('%d.%m.%Y')})"}
