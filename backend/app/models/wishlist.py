from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Wishlist(Base):
    """Модель избранного."""

    __tablename__ = "wishlist"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id"),
        Index("ix_wishlist_user_id", "user_id"),
        Index("ix_wishlist_tenant_id", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)

    product: Mapped["Product"] = relationship()

    def __repr__(self) -> str:
        return f"<Wishlist(user_id={self.user_id}, product_id={self.product_id})>"
