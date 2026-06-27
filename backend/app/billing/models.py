"""Billing models — subscriptions, invoices, payments."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Subscription(Base):
    """Tenant subscription to a plan."""
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_tenant_id", "tenant_id"),
        Index("ix_subscriptions_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tenant: Mapped["Tenant"] = relationship()
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription(tenant_id={self.tenant_id}, plan='{self.plan}', status='{self.status}')>"


class Invoice(Base):
    """Billing invoice."""
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    subscription_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    subscription: Mapped["Subscription"] = relationship(back_populates="invoices")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, amount={self.amount}, status='{self.status}')>"


class Payment(Base):
    """Payment record."""
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    invoice_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("invoices.id"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    method: Mapped[str] = mapped_column(String(50), nullable=False, default="card")
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, status='{self.status}')>"
