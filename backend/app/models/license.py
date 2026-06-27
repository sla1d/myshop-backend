from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Tenant(Base):
    """Магазин (tenant) — основная сущность multi-tenant архитектуры."""
    __tablename__ = "tenants"
    __table_args__ = (
        {"schema": None},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    subscription_status: Mapped[str] = mapped_column(String(20), default="active")
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)

    theme: Mapped[str] = mapped_column(String(50), default="midnight")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # White-label
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    footer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    hide_myshop_branding: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_email_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_role: Mapped[str | None] = mapped_column(String(50), nullable=True, default="user")

    license: Mapped["License"] = relationship(back_populates="tenant", uselist=False)
    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    products: Mapped[list["Product"]] = relationship(back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, slug='{self.slug}', plan='{self.plan}')>"


class License(Base):
    """Лицензия клиента."""
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), unique=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), default="starter")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_products: Mapped[int] = mapped_column(Integer, default=100)
    max_orders: Mapped[int] = mapped_column(Integer, default=1000)
    max_images: Mapped[int] = mapped_column(Integer, default=500)
    max_admins: Mapped[int] = mapped_column(Integer, default=3)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="license")

    def __repr__(self) -> str:
        return f"<License(tenant_id={self.tenant_id}, plan='{self.plan}')>"


# Тарифы SaaS
PLANS = {
    "starter": {
        "name": "Starter",
        "max_products": 100,
        "max_orders": 1000,
        "max_images": 500,
        "max_admins": 3,
        "price_monthly": 990,
        "price_yearly": 9900,
        "features": ["Каталог товаров", "Заказы", "Корзина", "Базовая аналитика"],
    },
    "business": {
        "name": "Business",
        "max_products": 1000,
        "max_orders": 10000,
        "max_images": 5000,
        "max_admins": 10,
        "price_monthly": 2990,
        "price_yearly": 29900,
        "features": ["Все из Starter", "Промокоды", "Отзывы", "Рассылки", "Расширенная аналитика"],
    },
    "pro": {
        "name": "Pro",
        "max_products": -1,
        "max_orders": -1,
        "max_images": -1,
        "max_admins": -1,
        "price_monthly": 9990,
        "price_yearly": 99900,
        "features": ["Все из Business", "API доступ", "Кастомный домен", "Приоритетная поддержка", "Белый-label"],
    },
}

LICENSE_PLANS = PLANS
