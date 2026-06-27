"""CDEK (СДЭК) delivery integration."""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("myshop.delivery")

CDEK_API = "https://api.cdek.ru/v2"


class CdekService:
    """CDEK delivery service integration."""

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id or getattr(settings, "CDEK_CLIENT_ID", "")
        self.client_secret = client_secret or getattr(settings, "CDEK_CLIENT_SECRET", "")
        self._token: str = ""
        self._token_expires: float = 0

    async def _get_token(self) -> Optional[str]:
        """Get auth token from CDEK API."""
        if not self.client_id or not self.client_secret:
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{CDEK_API}/auth/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=10,
                )
                data = resp.json()
                self._token = data.get("access_token", "")
                return self._token
            except Exception as e:
                logger.error("CDEK auth failed: %s", e)
                return None

    async def calculate_delivery(
        self,
        from_city_code: int,
        to_city_code: int,
        weight: int = 500,
        length: int = 30,
        width: int = 20,
        height: int = 10,
    ) -> Optional[dict]:
        """Calculate delivery cost and time."""
        token = await self._get_token()
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{CDEK_API}/calculator/tariff",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "type": 1,
                        "currency": 1,
                        "tariff_id": 136,
                        "from_location": {"code": from_city_code},
                        "to_location": {"code": to_city_code},
                        "services": [{"code": "INS", "param": 0}],
                        "packages": [{
                            "weight": weight,
                            "length": length,
                            "width": width,
                            "height": height,
                        }],
                    },
                    timeout=15,
                )
                data = resp.json()
                if resp.status_code >= 400:
                    logger.error("CDEK calc error: %s", data)
                    return None
                return data
            except Exception as e:
                logger.error("CDEK request failed: %s", e)
                return None

    async def create_order(
        self,
        order_id: str,
        recipient_name: str,
        recipient_phone: str,
        to_city_code: int,
        address: str,
        weight: int = 500,
    ) -> Optional[dict]:
        """Create a delivery order in CDEK."""
        token = await self._get_token()
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{CDEK_API}/orders",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "number": order_id,
                        "type": 1,
                        "currency": 1,
                        "tariff_code": 136,
                        "recipient": {
                            "name": recipient_name,
                            "phones": [{"number": recipient_phone}],
                        },
                        "from_location": {"address": "Москва"},
                        "to_location": {
                            "code": to_city_code,
                            "address": address,
                        },
                        "services": [{"code": "INS", "param": 0}],
                        "packages": [{
                            "number": order_id,
                            "weight": weight,
                            "length": 30,
                            "width": 20,
                            "height": 10,
                        }],
                    },
                    timeout=15,
                )
                data = resp.json()
                if resp.status_code >= 400:
                    logger.error("CDEK order error: %s", data)
                    return None
                logger.info("CDEK order created: %s", order_id)
                return data
            except Exception as e:
                logger.error("CDEK order failed: %s", e)
                return None

    async def get_tracking(self, cdek_number: str) -> Optional[dict]:
        """Get delivery tracking status."""
        token = await self._get_token()
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{CDEK_API}/orders/tracking",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"cdek_number": cdek_number},
                    timeout=10,
                )
                return resp.json()
            except Exception as e:
                logger.error("CDEK tracking failed: %s", e)
                return None

    async def get_cities(self, query: str = "") -> Optional[list]:
        """Search CDEK cities."""
        token = await self._get_token()
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{CDEK_API}/location/cities",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"q": query, "size": 10},
                    timeout=10,
                )
                return resp.json().get("locations", [])
            except Exception as e:
                logger.error("CDEK cities search failed: %s", e)
                return None


# Singleton
cdek = CdekService()
