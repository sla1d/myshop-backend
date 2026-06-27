"""SaaS models — domains, feature flags, plugins."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CustomDomain(Base):
    """Custom domain for a tenant store."""
    __tablename__ = "custom_domains"
    __table_args__ = (
        Index("ix_custom_domains_domain", "domain"),
        Index("ix_custom_domains_tenant_id", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ssl_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dns_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<CustomDomain(domain='{self.domain}', verified={self.verified})>"


class TenantFeature(Base):
    """Feature flags for a tenant — enabled/disabled per plan."""
    __tablename__ = "tenant_features"
    __table_args__ = (
        Index("ix_tenant_features_tenant_id", "tenant_id"),
        Index("ix_tenant_features_feature_key", "feature_key"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    feature_key: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<TenantFeature(tenant={self.tenant_id}, feature='{self.feature_key}', enabled={self.enabled})>"


class Plugin(Base):
    """Installed plugin for a tenant."""
    __tablename__ = "plugins"
    __table_args__ = (
        Index("ix_plugins_tenant_id", "tenant_id"),
        Index("ix_plugins_plugin_key", "plugin_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    plugin_key: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Plugin(key='{self.plugin_key}', enabled={self.enabled})>"


# Available feature flags
FEATURE_FLAGS = {
    "reviews": {"name": "Отзывы", "description": "Система отзывов на товары"},
    "wishlist": {"name": "Избранное", "description": "Список избранных товаров"},
    "flash_sales": {"name": "Flash Sale", "description": "Временные скидки"},
    "promocodes": {"name": "Промокоды", "description": "Система промокодов"},
    "analytics": {"name": "Аналитика", "description": "Расширенная аналитика"},
    "ab_testing": {"name": "A/B Тесты", "description": "A/B тестирование"},
    "referrals": {"name": "Рефералы", "description": "Реферальная программа"},
    "loyalty": {"name": "Лояльность", "description": "Программа лояльности"},
    "loyalty_program": {"name": "Лояльность", "description": "Программа лояльности"},
    "email_marketing": {"name": "Рассылки", "description": "Email рассылки"},
    "telegram_bot": {"name": "Telegram", "description": "Telegram уведомления"},
    "custom_domain": {"name": "Свой домен", "description": "Кастомный домен"},
    "ai_assistant": {"name": "ИИ-помощник", "description": "AI-ассистент для управления"},
    "marketplace_sync": {"name": "Маркетплейсы", "description": "Синхронизация с WB/Ozon"},
}

# Default features per plan
PLAN_FEATURES = {
    "starter": ["reviews", "wishlist", "promocodes"],
    "business": ["reviews", "wishlist", "flash_sales", "promocodes", "analytics", "referrals", "loyalty", "email_marketing", "telegram_bot", "ai_assistant"],
    "pro": list(FEATURE_FLAGS.keys()),  # All features
}
