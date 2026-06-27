from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AdBanner(Base):
    """Рекламный баннер на главной."""

    __tablename__ = "ad_banners"
    __table_args__ = (
        Index("ix_ad_banners_active", "active"),
        Index("ix_ad_banners_tenant_id", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AdBanner(id={self.id}, title='{self.title}')>"


class WishlistPrice(Base):
    """История цен для Wishlist-тревог."""

    __tablename__ = "wishlist_prices"
    __table_args__ = (
        Index("ix_wishlist_prices_user_id", "user_id"),
        Index("ix_wishlist_prices_tenant_id", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_add: Mapped[int] = mapped_column(Integer, nullable=False)
    notified_price_drop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notified_low_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<WishlistPrice(user={self.user_id}, product={self.product_id})>"
