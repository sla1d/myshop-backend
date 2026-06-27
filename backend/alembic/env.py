import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.database.base import Base

# Импорт ВСЕХ моделей для autogenerate
from app.models.user import User  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.cart import Cart  # noqa: F401
from app.models.order import Order, OrderItem  # noqa: F401
from app.models.order_status_history import OrderStatusHistory  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.wishlist import Wishlist  # noqa: F401
from app.models.promo import PromoCode  # noqa: F401
from app.models.license import Tenant, License  # noqa: F401
from app.models.flash_sale import FlashSale  # noqa: F401
from app.models.ab_test import ABTest, ABTestAssignment  # noqa: F401
from app.models.ad_banner import AdBanner, WishlistPrice  # noqa: F401
from app.billing.models import Subscription, Invoice, Payment  # noqa: F401
from app.rbac.models import Role, Permission, RolePermission, UserRole  # noqa: F401
from app.security.models import RefreshToken, LoginAttempt, AuditLog, SecurityEvent  # noqa: F401
from app.saas.models import CustomDomain, TenantFeature, Plugin  # noqa: F401

config = context.config

# Поддержка DATABASE_URL из окружения
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме (только генерация SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запуск миграций в online-режиме с async engine."""
    url = config.get_main_option("sqlalchemy.url")
    connectable = async_engine_from_config(
        {"sqlalchemy.url": url} if url else {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
