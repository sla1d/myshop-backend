"""Feature flags service — enable/disable features per tenant."""
import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.saas.models import FEATURE_FLAGS, PLAN_FEATURES, TenantFeature, CustomDomain

logger = logging.getLogger("myshop.features")


class FeatureService:
    """Service for managing feature flags."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_features(self, tenant_id: int) -> dict[str, bool]:
        """Get all feature flags for a tenant."""
        result = await self.session.execute(
            select(TenantFeature).where(TenantFeature.tenant_id == tenant_id)
        )
        features = result.scalars().all()
        return {f.feature_key: f.enabled for f in features}

    async def is_enabled(self, tenant_id: int, feature_key: str) -> bool:
        """Check if a feature is enabled for a tenant."""
        result = await self.session.execute(
            select(TenantFeature).where(
                TenantFeature.tenant_id == tenant_id,
                TenantFeature.feature_key == feature_key,
            )
        )
        feature = result.scalar_one_or_none()
        return feature.enabled if feature else False

    async def set_feature(
        self, tenant_id: int, feature_key: str, enabled: bool,
        config: dict | None = None,
    ) -> TenantFeature:
        """Enable or disable a feature."""
        if feature_key not in FEATURE_FLAGS:
            raise ValueError(f"Unknown feature: {feature_key}")

        result = await self.session.execute(
            select(TenantFeature).where(
                TenantFeature.tenant_id == tenant_id,
                TenantFeature.feature_key == feature_key,
            )
        )
        feature = result.scalar_one_or_none()

        if feature:
            feature.enabled = enabled
            if config:
                feature.config_json = json.dumps(config, ensure_ascii=False)
        else:
            feature = TenantFeature(
                tenant_id=tenant_id,
                feature_key=feature_key,
                enabled=enabled,
                config_json=json.dumps(config, ensure_ascii=False) if config else None,
            )
            self.session.add(feature)

        await self.session.flush()
        logger.info("Feature %s=%s for tenant=%d", feature_key, enabled, tenant_id)
        return feature

    async def init_plan_features(self, tenant_id: int, plan: str) -> None:
        """Initialize features for a tenant based on plan."""
        default_features = PLAN_FEATURES.get(plan, PLAN_FEATURES["starter"])
        for feature_key, info in FEATURE_FLAGS.items():
            enabled = feature_key in default_features
            await self.set_feature(tenant_id, feature_key, enabled)

    async def get_available_features(self) -> dict:
        """Get all available features with descriptions."""
        return FEATURE_FLAGS


class DomainService:
    """Service for custom domain management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_domains(self, tenant_id: int) -> list[CustomDomain]:
        result = await self.session.execute(
            select(CustomDomain).where(CustomDomain.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def add_domain(self, tenant_id: int, domain: str) -> CustomDomain:
        """Add a custom domain."""
        dc = CustomDomain(
            tenant_id=tenant_id,
            domain=domain,
            verified=False,
            ssl_enabled=False,
        )
        self.session.add(dc)
        await self.session.flush()
        logger.info("Domain added: %s for tenant=%d", domain, tenant_id)
        return dc

    async def verify_domain(self, domain_id: int) -> bool:
        """Mark domain as verified (called after DNS check)."""
        dc = await self.session.get(CustomDomain, domain_id)
        if not dc:
            return False
        dc.verified = True
        dc.dns_configured = True
        await self.session.flush()
        return True

    async def get_primary_domain(self, tenant_id: int) -> Optional[CustomDomain]:
        result = await self.session.execute(
            select(CustomDomain).where(
                CustomDomain.tenant_id == tenant_id,
                CustomDomain.verified == True,
            ).limit(1)
        )
        return result.scalars().first()
