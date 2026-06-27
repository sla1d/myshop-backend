"""Telegram Bot integration — notifications, orders, support."""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("myshop.telegram")

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramService:
    """Telegram Bot API wrapper for notifications."""

    def __init__(self, bot_token: str = ""):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN

    @property
    def _base_url(self) -> str:
        return TELEGRAM_API.format(token=self.bot_token)

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> Optional[dict]:
        """Send a text message."""
        if not self.bot_token:
            logger.debug("Telegram bot token not configured")
            return None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_notification": disable_notification,
                    },
                    timeout=10,
                )
                data = resp.json()
                if not data.get("ok"):
                    logger.warning("Telegram send failed: %s", data.get("description"))
                return data
            except Exception as e:
                logger.error("Telegram error: %s", e)
                return None

    async def send_order_notification(
        self,
        chat_id: int | str,
        order_id: int,
        total: int,
        address: str,
        status: str = "pending",
    ) -> Optional[dict]:
        """Send order notification with formatted text."""
        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "shipped": "🚚",
            "delivered": "✅",
            "cancelled": "❌",
        }
        emoji = status_emoji.get(status, "📦")

        text = (
            f"📦 <b>Новый заказ #{order_id}</b>\n\n"
            f"{emoji} Статус: <b>{status}</b>\n"
            f"💰 Сумма: <b>{total:,} ₽</b>\n"
            f"📍 Адрес: {address}\n\n"
            f"🔗 <a href='https://myshop.com/admin/orders/{order_id}'>Управление</a>"
        )
        return await self.send_message(chat_id, text)

    async def send_delivery_update(
        self,
        chat_id: int | str,
        order_id: int,
        status: str,
        tracking_number: str = "",
    ) -> Optional[dict]:
        """Send delivery status update."""
        text = (
            f"🚚 <b>Обновление доставки #{order_id}</b>\n\n"
            f"📦 Статус: <b>{status}</b>\n"
        )
        if tracking_number:
            text += f"🔢 Трек-номер: <code>{tracking_number}</code>\n"

        return await self.send_message(chat_id, text)


# Singleton
telegram = TelegramService()
