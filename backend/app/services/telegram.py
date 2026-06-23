"""Telegram бот для уведомлений о заказах."""
import logging

from aiogram import Bot
from aiogram.types import Message

from app.core.config import settings

logger = logging.getLogger("myshop.telegram")

_bot: Bot | None = None


def get_bot() -> Bot | None:
    """Получить экземпляр бота (ленивая инициализация)."""
    global _bot
    if _bot is None and settings.TELEGRAM_BOT_TOKEN:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


async def send_message(chat_id: int, text: str) -> bool:
    """Отправить сообщение в Telegram."""
    bot = get_bot()
    if not bot:
        logger.warning("Telegram bot not configured")
        return False
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        return True
    except Exception as e:
        logger.error("Telegram send error: %s", e)
        return False


async def notify_order_created(chat_id: int, order_id: int, total: int, address: str) -> bool:
    """Уведомление о новом заказе."""
    text = (
        f"🛒 <b>Новый заказ #{order_id}</b>\n\n"
        f"💰 Сумма: {total} ₽\n"
        f"📍 Адрес: {address}\n\n"
        f"Статус: В обработке"
    )
    return await send_message(chat_id, text)


async def notify_order_status(chat_id: int, order_id: int, status: str) -> bool:
    """Уведомление об изменении статуса."""
    status_emoji = {
        "processing": "⚙️",
        "shipped": "🚚",
        "delivered": "✅",
        "cancelled": "❌",
    }
    emoji = status_emoji.get(status, "📦")
    text = f"{emoji} <b>Заказ #{order_id}</b>\n\nСтатус: {status}"
    return await send_message(chat_id, text)


async def notify_promo(chat_id: int, code: str, discount: int) -> bool:
    """Уведомление о промокоде."""
    text = (
        f"🎉 <b>Специально для вас!</b>\n\n"
        f"Промокод: <code>{code}</code>\n"
        f"Скидка: {discount}%\n\n"
        f"Действует в вашем магазине!"
    )
    return await send_message(chat_id, text)
