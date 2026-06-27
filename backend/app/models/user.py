from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_role", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(10), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)

    # 2FA (TOTP)
    two_factor_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Recovery codes for 2FA
    recovery_codes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Реферальная программа
    referral_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    referred_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referral_earnings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Лояльность / кэшбэк
    loyalty_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loyalty_level: Mapped[str] = mapped_column(String(20), nullable=False, default="bronze")

    cart_items: Mapped[list["Cart"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tenant: Mapped["Tenant | None"] = relationship(back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user", foreign_keys="[UserRole.user_id]")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

    async def has_permission(self, permission_name: str, session: AsyncSession, tenant_id: int | None = None) -> bool:
        """Check if user has a specific permission.

        Args:
            permission_name: e.g. "product.create", "order.view"
            session: async SQLAlchemy session
            tenant_id: tenant context (defaults to self.tenant_id)
        """
        from sqlalchemy import select
        from app.rbac.models import UserRole, Role, Permission, RolePermission

        tid = tenant_id or self.tenant_id

        # Superadmin bypass
        if self.role == "superadmin":
            return True

        stmt = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == self.id)
        )

        if tid is not None:
            stmt = stmt.where(UserRole.tenant_id == tid)

        result = await session.execute(stmt)
        permissions = {r[0] for r in result.all()}
        return permission_name in permissions

    async def get_permissions(self, session: AsyncSession, tenant_id: int | None = None) -> set[str]:
        """Get all permission names for this user."""
        from sqlalchemy import select
        from app.rbac.models import UserRole, Role, Permission, RolePermission

        tid = tenant_id or self.tenant_id

        if self.role == "superadmin":
            result = await session.execute(select(Permission.name))
            return {r[0] for r in result.all()}

        stmt = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == self.id)
        )

        if tid is not None:
            stmt = stmt.where(UserRole.tenant_id == tid)

        result = await session.execute(stmt)
        return {r[0] for r in result.all()}

    async def get_roles(self, session: AsyncSession, tenant_id: int | None = None) -> list[str]:
        """Get all role names for this user."""
        from sqlalchemy import select
        from app.rbac.models import UserRole, Role

        tid = tenant_id or self.tenant_id

        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == self.id)
        )

        if tid is not None:
            stmt = stmt.where(UserRole.tenant_id == tid)

        result = await session.execute(stmt)
        return [r[0] for r in result.all()]
