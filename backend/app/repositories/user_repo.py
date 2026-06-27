"""User repository."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(self, tenant_id: int) -> Sequence[User]:
        return await self.get_all(filters={"tenant_id": tenant_id})

    async def get_admins(self, tenant_id: int) -> Sequence[User]:
        result = await self.session.execute(
            select(User).where(User.tenant_id == tenant_id, User.role == "admin")
        )
        return result.scalars().all()
