"""RBAC dependencies — permission checking for FastAPI."""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.user import User

logger = logging.getLogger("myshop.rbac")


class RequirePermission:
    """Dependency that checks if current user has a specific permission.

    Usage:
        @router.get("/products")
        async def list_products(
            user: User = Depends(RequirePermission("product.view")),
        ):
            ...
    """

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> User:
        # Superadmin bypass
        if user.role == "superadmin":
            return user

        tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id

        has_perm = await user.has_permission(self.permission, session, tenant_id)
        if not has_perm:
            logger.warning(
                "Permission denied: user=%s, perm=%s, path=%s",
                user.username, self.permission, request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав: требуется '{self.permission}'",
            )
        return user


class RequireAnyPermission:
    """Check if user has ANY of the listed permissions."""

    def __init__(self, *permissions: str):
        self.permissions = permissions

    async def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> User:
        tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id

        for perm in self.permissions:
            if await user.has_permission(perm, session, tenant_id):
                return user

        logger.warning(
            "Permission denied: user=%s, perms=%s, path=%s",
            user.username, self.permissions, request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Недостаточно прав: требуется одно из {self.permissions}",
        )


class RequireAllPermissions:
    """Check if user has ALL of the listed permissions."""

    def __init__(self, *permissions: str):
        self.permissions = permissions

    async def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> User:
        tenant_id = getattr(request.state, "tenant_id", None) or user.tenant_id

        for perm in self.permissions:
            if not await user.has_permission(perm, session, tenant_id):
                logger.warning(
                    "Permission denied: user=%s, missing=%s, path=%s",
                    user.username, perm, request.url.path,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Недостаточно прав: требуется '{perm}'",
                )
        return user


# Convenience aliases
RequireAdmin = RequirePermission("tenant.manage")
RequireOwner = RequirePermission("tenant.manage")  # owner has all perms via is_system
