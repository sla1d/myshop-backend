"""YooKassa (ЮKassa) payment integration."""
import base64
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("myshop.payments")

YOOKASSA_API = "https://api.yookassa.ru/v3"


class YooKassaService:
    """YooKassa payment gateway integration."""

    def __init__(self, shop_id: str = "", secret_key: str = ""):
        self.shop_id = shop_id or getattr(settings, "YOOKASSA_SHOP_ID", "")
        self.secret_key = secret_key or getattr(settings, "YOOKASSA_SECRET_KEY", "")

    @property
    def _auth(self) -> str:
        """Basic auth header."""
        credentials = f"{self.shop_id}:{self.secret_key}"
        return base64.b64encode(credentials.encode()).decode()

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
            "Idempotence-Key": "",  # Set per request
        }

    async def create_payment(
        self,
        amount: int,
        currency: str = "RUB",
        description: str = "",
        return_url: str = "",
        metadata: dict | None = None,
        idempotency_key: str = "",
    ) -> Optional[dict]:
        """Create a payment with idempotency key."""
        if not self.shop_id or not self.secret_key:
            logger.debug("YooKassa not configured")
            return None

        import uuid
        key = idempotency_key or str(uuid.uuid4())
        headers = {**self._headers, "Idempotence-Key": key}

        payload = {
            "amount": {
                "value": f"{amount / 100:.2f}" if amount > 100 else str(amount),
                "currency": currency,
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://myshop.com/payment/success",
            },
            "capture": True,
            "description": description,
        }

        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{YOOKASSA_API}/payments",
                    headers=headers,
                    json=payload,
                    timeout=15,
                )
                data = resp.json()
                if resp.status_code >= 400:
                    logger.error("YooKassa error: %s", data)
                    return None
                logger.info("Payment created: %s", data.get("id"))
                return data
            except Exception as e:
                logger.error("YooKassa request failed: %s", e)
                return None

    async def get_payment(self, payment_id: str) -> Optional[dict]:
        """Get payment status."""
        if not self.shop_id or not self.secret_key:
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{YOOKASSA_API}/payments/{payment_id}",
                    headers=self._headers,
                    timeout=10,
                )
                return resp.json()
            except Exception as e:
                logger.error("YooKassa get_payment failed: %s", e)
                return None

    async def refund_payment(
        self,
        payment_id: str,
        amount: int,
        reason: str = "",
    ) -> Optional[dict]:
        """Refund a payment."""
        import uuid

        if not self.shop_id or not self.secret_key:
            return None

        idempotency_key = str(uuid.uuid4())
        headers = {**self._headers, "Idempotence-Key": idempotency_key}

        payload = {
            "payment_id": payment_id,
            "amount": {
                "value": f"{amount / 100:.2f}" if amount > 100 else str(amount),
                "currency": "RUB",
            },
        }
        if reason:
            payload["description"] = reason

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{YOOKASSA_API}/refunds",
                    headers=headers,
                    json=payload,
                    timeout=15,
                )
                return resp.json()
            except Exception as e:
                logger.error("YooKassa refund failed: %s", e)
                return None


# Singleton
yookassa = YooKassaService()
