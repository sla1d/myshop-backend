"""RBAC seed data — roles, permissions, assignments."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.models import Permission, Role, RolePermission

logger = logging.getLogger("myshop.rbac")

# ─── All Permissions ────────────────────────────────
PERMISSIONS = [
    # Products
    ("product.create", "Создавать товары", "products"),
    ("product.update", "Редактировать товары", "products"),
    ("product.delete", "Удалять товары", "products"),
    ("product.view", "Просматривать товары", "products"),
    # Orders
    ("order.view", "Просматривать заказы", "orders"),
    ("order.update", "Обновлять статусы заказов", "orders"),
    ("order.cancel", "Отменять заказы", "orders"),
    # Billing
    ("billing.view", "Просматривать биллинг", "billing"),
    ("billing.manage", "Управлять подписками и счетами", "billing"),
    # Analytics
    ("analytics.view", "Просматривать аналитику", "analytics"),
    ("analytics.export", "Экспортировать данные аналитики", "analytics"),
    # Users
    ("user.invite", "Приглашать пользователей", "users"),
    ("user.update", "Редактировать профили пользователей", "users"),
    ("user.delete", "Удалять пользователей", "users"),
    ("user.assign_role", "Назначать роли", "users"),
    # Tenant
    ("tenant.manage", "Управлять настройками магазина", "tenant"),
    ("tenant.billing", "Управлять подпиской", "tenant"),
    # AI
    ("ai.generate_banner", "Генерировать баннеры через ИИ", "ai"),
    ("ai.generate_description", "Генерировать описания через ИИ", "ai"),
    ("ai.create_campaign", "Создавать рекламные кампании через ИИ", "ai"),
    ("ai.manage", "Управлять настройками ИИ", "ai"),
    # Promos & Reviews
    ("promo.create", "Создавать промокоды", "promos"),
    ("promo.update", "Редактировать промокоды", "promos"),
    ("promo.delete", "Удалять промокоды", "promos"),
    ("review.moderate", "Модерировать отзывы", "reviews"),
    # Integrations
    ("integration.manage", "Управлять интеграциями", "integrations"),
    # Audit
    ("audit.view", "Просматривать аудит-лог", "audit"),
    # Support
    ("support.respond", "Отвечать в чате поддержки", "support"),
]

# ─── Roles with their permissions ──────────────────
ROLES = {
    "owner": {
        "description": "Владелец магазина — полный доступ",
        "permissions": [p[0] for p in PERMISSIONS],  # All permissions
    },
    "admin": {
        "description": "Администратор — почти полный доступ",
        "permissions": [
            "product.create", "product.update", "product.delete", "product.view",
            "order.view", "order.update", "order.cancel",
            "billing.view", "billing.manage",
            "analytics.view", "analytics.export",
            "user.invite", "user.update", "user.delete", "user.assign_role",
            "promo.create", "promo.update", "promo.delete",
            "review.moderate",
            "integration.manage",
            "audit.view",
            "ai.generate_banner", "ai.generate_description", "ai.create_campaign", "ai.manage",
            "support.respond",
        ],
    },
    "product_manager": {
        "description": "Менеджер товаров — управление каталогом",
        "permissions": [
            "product.create", "product.update", "product.delete", "product.view",
            "promo.create", "promo.update", "promo.delete",
            "analytics.view",
            "ai.generate_description",
        ],
    },
    "order_manager": {
        "description": "Менеджер заказов — обработка заказов",
        "permissions": [
            "product.view",
            "order.view", "order.update", "order.cancel",
            "analytics.view",
            "support.respond",
        ],
    },
    "content_editor": {
        "description": "Контент-менеджер — контент и дизайн",
        "permissions": [
            "product.view",
            "product.update",
            "promo.create", "promo.update",
            "review.moderate",
            "ai.generate_banner", "ai.generate_description",
        ],
    },
    "support": {
        "description": "Поддержка — помощь покупателям",
        "permissions": [
            "product.view",
            "order.view",
            "support.respond",
            "review.moderate",
        ],
    },
    "analyst": {
        "description": "Аналитик — только просмотр",
        "permissions": [
            "product.view",
            "order.view",
            "analytics.view", "analytics.export",
            "audit.view",
        ],
    },
    "ai_manager": {
        "description": "Менеджер ИИ — управление AI функциями",
        "permissions": [
            "product.view",
            "ai.generate_banner", "ai.generate_description", "ai.create_campaign", "ai.manage",
            "analytics.view",
        ],
    },
}


async def seed_rbac(session: AsyncSession) -> None:
    """Seed RBAC roles and permissions if not present."""
    # Check if permissions exist
    result = await session.execute(select(Permission).limit(1))
    if result.scalars().first() is not None:
        return  # Already seeded

    # Create permissions
    perm_map = {}
    for name, description, category in PERMISSIONS:
        perm = Permission(name=name, description=description, category=category)
        session.add(perm)
        await session.flush()
        perm_map[name] = perm.id

    # Create roles and assign permissions
    for role_name, role_config in ROLES.items():
        role = Role(
            name=role_name,
            description=role_config["description"],
            is_system=True,
        )
        session.add(role)
        await session.flush()

        for perm_name in role_config["permissions"]:
            if perm_name in perm_map:
                rp = RolePermission(
                    role_id=role.id,
                    permission_id=perm_map[perm_name],
                )
                session.add(rp)

    await session.commit()
    logger.info("RBAC seeded: %d permissions, %d roles", len(PERMISSIONS), len(ROLES))


async def assign_owner_role(session: AsyncSession, user_id: int, tenant_id: int) -> None:
    """Assign 'owner' role to a user for a tenant."""
    from app.rbac.models import UserRole

    result = await session.execute(select(Role).where(Role.name == "owner"))
    owner_role = result.scalar_one_or_none()
    if not owner_role:
        return

    # Check if already assigned
    existing = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            UserRole.role_id == owner_role.id,
        )
    )
    if existing.scalar_one_or_none():
        return

    ur = UserRole(
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=owner_role.id,
    )
    session.add(ur)
    await session.commit()
    logger.info("Owner role assigned: user=%d, tenant=%d", user_id, tenant_id)
