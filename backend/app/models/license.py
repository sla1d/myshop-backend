from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Tenant(Base):
    """Клиент (магазин)."""
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    license: Mapped[Optional["License"]] = relationship(back_populates="tenant", uselist=False)
    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class License(Base):
    """Лицензия клиента."""
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), unique=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), default="starter")  # starter/pro/enterprise
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    max_products: Mapped[int] = mapped_column(Integer, default=100)
    max_users: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="license")


# Планы
LICENSE_PLANS = {
    "starter": {"max_products": 100, "max_users": 10, "price": 2990},
    "pro": {"max_products": 1000, "max_users": 50, "price": 7990},
    "enterprise": {"max_products": -1, "max_users": -1, "price": 19990},  # -1 = безлимит
}
