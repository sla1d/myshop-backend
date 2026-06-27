"""Payment provider abstraction — supports multiple providers."""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("myshop.payments")


class PaymentProvider(ABC):
    """Abstract payment provider interface."""

    @abstractmethod
    async def create_payment(
        self,
        amount: int,
        currency: str = "RUB",
        description: str = "",
        return_url: str = "",
        metadata: dict | None = None,
    ) -> Optional[dict]:
        """Create a payment. Returns payment URL and ID."""
        pass

    @abstractmethod
    async def get_payment(self, payment_id: str) -> Optional[dict]:
        """Get payment status."""
        pass

    @abstractmethod
    async def refund(self, payment_id: str, amount: int, reason: str = "") -> Optional[dict]:
        """Refund a payment."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class YooKassaProvider(PaymentProvider):
    """YooKassa payment provider."""

    def __init__(self):
        from app.integrations.yookassa import yookassa
        self._yookassa = yookassa

    def is_configured(self) -> bool:
        return bool(getattr(settings, "YOOKASSA_SHOP_ID", ""))

    async def create_payment(self, amount, currency="RUB", description="", return_url="", metadata=None):
        return await self._yookassa.create_payment(amount, currency, description, return_url, metadata)

    async def get_payment(self, payment_id):
        return await self._yookassa.get_payment(payment_id)

    async def refund(self, payment_id, amount, reason=""):
        return await self._yookassa.refund_payment(payment_id, amount, reason)


class StripeProvider(PaymentProvider):
    """Stripe payment provider (placeholder)."""

    def is_configured(self) -> bool:
        return bool(getattr(settings, "STRIPE_SECRET_KEY", ""))

    async def create_payment(self, amount, currency="RUB", description="", return_url="", metadata=None):
        logger.warning("Stripe not implemented")
        return None

    async def get_payment(self, payment_id):
        return None

    async def refund(self, payment_id, amount, reason=""):
        return None


class CloudPaymentsProvider(PaymentProvider):
    """CloudPayments payment provider (placeholder)."""

    def is_configured(self) -> bool:
        return bool(getattr(settings, "CLOUDPAYMENTS_PUBLIC_ID", ""))

    async def create_payment(self, amount, currency="RUB", description="", return_url="", metadata=None):
        logger.warning("CloudPayments not implemented")
        return None

    async def get_payment(self, payment_id):
        return None

    async def refund(self, payment_id, amount, reason=""):
        return None


class PaymentProviderFactory:
    """Factory for creating payment providers."""

    _providers: dict[str, type[PaymentProvider]] = {
        "yookassa": YooKassaProvider,
        "stripe": StripeProvider,
        "cloudpayments": CloudPaymentsProvider,
    }

    @classmethod
    def get_provider(cls, name: str = "yookassa") -> PaymentProvider:
        """Get a payment provider by name."""
        provider_class = cls._providers.get(name)
        if not provider_class:
            raise ValueError(f"Unknown payment provider: {name}. Available: {list(cls._providers.keys())}")
        return provider_class()

    @classmethod
    def get_configured_provider(cls) -> Optional[PaymentProvider]:
        """Get the first configured payment provider."""
        for name in cls._providers:
            provider = cls.get_provider(name)
            if provider.is_configured():
                return provider
        return None

    @classmethod
    def register(cls, name: str, provider_class: type[PaymentProvider]) -> None:
        """Register a custom payment provider."""
        cls._providers[name] = provider_class


# Singleton — get configured provider
def get_payment_provider(name: str | None = None) -> PaymentProvider:
    """Get payment provider by name or auto-detect configured."""
    if name:
        return PaymentProviderFactory.get_provider(name)
    provider = PaymentProviderFactory.get_configured_provider()
    if provider is None:
        logger.warning("No payment provider configured, using YooKassa fallback")
        return YooKassaProvider()
    return provider
