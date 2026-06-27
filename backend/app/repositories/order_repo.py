"""Order repository."""
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for Order model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_with_items(self, order_id: int) -> Optional[Order]:
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload("product"))
            .where(Order.id == order_id)
        )
        return result.scalars().unique().one_or_none()

    async def get_by_user(self, user_id: int, limit: int = 50) -> Sequence[Order]:
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .limit(limit)
        )
        return result.scalars().unique().all()

    async def get_by_tenant(self, tenant_id: int, limit: int = 100) -> Sequence[Order]:
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.tenant_id == tenant_id)
            .order_by(Order.id.desc())
            .limit(limit)
        )
        return result.scalars().unique().all()

    async def count_by_status(self, tenant_id: int | None = None) -> dict:
        stmt = select(Order.status, func.count(Order.id)).group_by(Order.status)
        if tenant_id is not None:
            stmt = stmt.where(Order.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return {r[0]: r[1] for r in result.all()}

    async def get_revenue(
        self,
        tenant_id: int | None = None,
        days: int | None = None,
    ) -> int:
        from datetime import datetime, timedelta, timezone

        stmt = select(func.coalesce(func.sum(Order.total), 0))
        if tenant_id is not None:
            stmt = stmt.where(Order.tenant_id == tenant_id)
        if days is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(Order.created_at >= since)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
