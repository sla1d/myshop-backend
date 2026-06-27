"""WhatsApp Business API integration — send order notifications."""
import logging
from typing import Any

import httpx

logger = logging.getLogger("myshop.integrations.whatsapp")


class WhatsAppService:
    """Send messages via WhatsApp Business API."""

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"

    async def send_text(self, to: str, text: str) -> dict[str, Any]:
        """Send a text message."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()

    async def send_order_confirmation(
        self, to: str, order_id: int, total: int, address: str
    ) -> dict[str, Any]:
        """Send order confirmation template."""
        text = (
            f"✅ Заказ #{order_id} оформлен!\n\n"
            f"Сумма: {total} ₽\n"
            f"Адрес: {address}\n\n"
            f"Спасибо за покупку!"
        )
        return await self.send_text(to, text)

    async def send_status_update(
        self, to: str, order_id: int, status: str
    ) -> dict[str, Any]:
        """Send order status update."""
        status_map = {
            "processing": "📦 Заказ обрабатывается",
            "shipped": "🚚 Заказ отправлен",
            "delivered": "✅ Заказ доставлен",
            "cancelled": "❌ Заказ отменён",
        }
        text = status_map.get(status, f"Статус заказа #{order_id}: {status}")
        return await self.send_text(to, text)


_instance: WhatsAppService | None = None


def get_whatsapp(phone_number_id: str = "", access_token: str = "") -> WhatsAppService | None:
    global _instance
    if _instance is None and phone_number_id and access_token:
        _instance = WhatsAppService(phone_number_id, access_token)
    return _instance
