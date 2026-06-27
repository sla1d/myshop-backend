"""AI Assistant — natural language store management."""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.license import Tenant, PLANS
from app.models.product import Product
from app.models.ad_banner import AdBanner
from app.models.promo import PromoCode

logger = logging.getLogger("myshop.ai")

# Intent patterns (Russian + English)
INTENT_PATTERNS = {
    "change_theme": {
        "patterns": [
            r"(?:смени|измени|установи|поставь)\s+(?:тему|тему на|color|theme)\s*(?:на\s*)?(\w+)",
            r"(?:theme|цвет|цветовая схема)\s*(?:на\s+|=)\s*(\w+)",
            r"(?:dark|dark mode|тёмная|светлая|light|midnight|nature|rose|cyber|minimal)",
        ],
        "handler": "_handle_theme",
    },
    "enable_feature": {
        "patterns": [
            r"(?:включи|добавь|активируй|включить)\s+(отзывы|reviews|промокод|промокоды|promocodes|избранное|wishlist|flash\s*sale|рассылку|лояльность|реферальн)",
        ],
        "handler": "_handle_enable_feature",
    },
    "disable_feature": {
        "patterns": [
            r"(?:выключи|убери|деактивируй|отключи)\s+(отзывы|reviews|промокод|промокоды|promocodes|избранное|wishlist|flash\s*sale|рассылку|лояльность|реферальн)",
        ],
        "handler": "_handle_disable_feature",
    },
    "create_banner": {
        "patterns": [
            r"(?:создай|добавь|сделай)\s+(?:баннер|баннер|banner)\s+(?:\«|\"|')(.+?)(?:\»|\"|')",
            r"(?:banner|баннер)\s+(?:\«|\"|')(.+?)(?:\»|\"|')",
        ],
        "handler": "_handle_create_banner",
    },
    "create_promo": {
        "patterns": [
            r"(?:создай|добавь|сделай)\s+(?:промокод|промо|promo)\s+(\w+)\s+(?:на|со\s+скидкой)\s+(\d+)\s*%?",
            r"(?:промокод|promo)\s+(\w+)\s+(\d+)\s*%",
        ],
        "handler": "_handle_create_promo",
    },
    "set_name": {
        "patterns": [
            r"(?:смени|измени|установи|назови)\s+(?:название|имя|name)\s+(?:на\s+|=)\s*(.+)",
            r"(?:название|name)\s*(?:на\s+|=)\s*(.+)",
        ],
        "handler": "_handle_set_name",
    },
    "get_stats": {
        "patterns": [
            r"(?:покажи|сколько|выведи)\s+(?:статистик|стати|stats|analytics|продажи|заказы)",
            r"(?:статистика|стати|stats|аналитика)",
        ],
        "handler": "_handle_get_stats",
    },
    "help": {
        "patterns": [
            r"(?:помощь|помоги|help|что ты умеешь|что можешь|команды)",
        ],
        "handler": "_handle_help",
    },
}

THEMES = ["midnight", "light", "nature", "rose", "cyber", "minimal"]
THEME_ALIASES = {
    "dark": "midnight", "тёмная": "midnight", "dark mode": "midnight",
    "светлая": "light", "light": "light",
    "природа": "nature", "nature": "nature",
    "розовая": "rose", "rose": "rose", "pink": "rose",
    "кибер": "cyber", "cyber": "cyber",
    "минимализм": "minimal", "minimal": "minimal",
}

FEATURE_MAP = {
    "отзывы": "reviews", "reviews": "reviews",
    "промокод": "promocodes", "промокоды": "promocodes", "promocodes": "promocodes",
    "избранное": "wishlist", "wishlist": "wishlist",
    "flash sale": "flash_sales", "флеш": "flash_sales",
    "лояльность": "loyalty", "loyalty": "loyalty",
    "реферальн": "referral", "referral": "referral",
}


class AIAssistant:
    """Natural language store management assistant."""

    def __init__(self, session: AsyncSession, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id
        self.tenant: Optional[Tenant] = None

    async def _load_tenant(self):
        if not self.tenant:
            self.tenant = await self.session.get(Tenant, self.tenant_id)

    async def process_message(self, message: str) -> dict:
        """Process a natural language message and execute the intent."""
        message_lower = message.lower().strip()

        for intent_name, intent_config in INTENT_PATTERNS.items():
            for pattern in intent_config["patterns"]:
                match = re.search(pattern, message_lower)
                if match:
                    handler = getattr(self, intent_config["handler"])
                    try:
                        return await handler(message, match)
                    except Exception as e:
                        logger.error("AI handler error: %s", e)
                        return {
                            "success": False,
                            "message": f"Ошибка при выполнении: {e}",
                            "intent": intent_name,
                        }

        return {
            "success": False,
            "message": "Не понял команду. Попробуйте 'помощь' для списка команд.",
            "intent": "unknown",
        }

    async def _handle_theme(self, message: str, match: re.Match) -> dict:
        theme_name = match.group(1) if match.lastindex else ""
        theme = THEME_ALIASES.get(theme_name, theme_name)

        if theme not in THEMES:
            return {
                "success": False,
                "message": f"Тема '{theme_name}' не найдена. Доступные: {', '.join(THEMES)}",
            }

        await self._load_tenant()
        if self.tenant:
            self.tenant.theme = theme
            await self.session.commit()

        return {
            "success": True,
            "message": f"Тема изменена на '{theme}'",
            "action": {"type": "theme_change", "value": theme},
        }

    async def _handle_enable_feature(self, message: str, match: re.Match) -> dict:
        feature_key = FEATURE_MAP.get(match.group(1), match.group(1))

        await self._load_tenant()
        if self.tenant:
            settings = json.loads(self.tenant.settings or "{}")
            settings[feature_key] = True
            self.tenant.settings = json.dumps(settings)
            await self.session.commit()

        return {
            "success": True,
            "message": f"Функция '{feature_key}' включена",
            "action": {"type": "feature_enable", "value": feature_key},
        }

    async def _handle_disable_feature(self, message: str, match: re.Match) -> dict:
        feature_key = FEATURE_MAP.get(match.group(1), match.group(1))

        await self._load_tenant()
        if self.tenant:
            settings = json.loads(self.tenant.settings or "{}")
            settings[feature_key] = False
            self.tenant.settings = json.dumps(settings)
            await self.session.commit()

        return {
            "success": True,
            "message": f"Функция '{feature_key}' отключена",
            "action": {"type": "feature_disable", "value": feature_key},
        }

    async def _handle_create_banner(self, message: str, match: re.Match) -> dict:
        title = match.group(1)

        banner = AdBanner(
            title=title,
            image_url="https://picsum.photos/seed/banner/800/200",
            active=True,
            tenant_id=self.tenant_id,
        )
        self.session.add(banner)
        await self.session.commit()
        await self.session.refresh(banner)

        return {
            "success": True,
            "message": f"Баннер '{title}' создан",
            "action": {"type": "banner_create", "banner_id": banner.id},
        }

    async def _handle_create_promo(self, message: str, match: re.Match) -> dict:
        code = match.group(1).upper()
        discount = int(match.group(2))

        from datetime import timedelta
        promo = PromoCode(
            code=code,
            discount_percent=discount,
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
            max_uses=100,
            tenant_id=self.tenant_id,
        )
        self.session.add(promo)
        await self.session.commit()

        return {
            "success": True,
            "message": f"Промокод '{code}' создан со скидкой {discount}%",
            "action": {"type": "promo_create", "code": code, "discount": discount},
        }

    async def _handle_set_name(self, message: str, match: re.Match) -> dict:
        name = match.group(1).strip()

        await self._load_tenant()
        if self.tenant:
            self.tenant.store_name = name
            self.tenant.name = name
            await self.session.commit()

        return {
            "success": True,
            "message": f"Название магазина изменено на '{name}'",
            "action": {"type": "name_change", "value": name},
        }

    async def _handle_get_stats(self, message: str, match: re.Match) -> dict:
        from app.models.order import Order
        from sqlalchemy import func

        products = (await self.session.execute(
            select(func.count(Product.id)).where(Product.tenant_id == self.tenant_id)
        )).scalar() or 0

        orders = (await self.session.execute(
            select(func.count(Order.id)).where(Order.tenant_id == self.tenant_id)
        )).scalar() or 0

        revenue = (await self.session.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(Order.tenant_id == self.tenant_id)
        )).scalar() or 0

        return {
            "success": True,
            "message": (
                f"📊 Статистика магазина:\n"
                f"📦 Товаров: {products}\n"
                f"🛒 Заказов: {orders}\n"
                f"💰 Выручка: {int(revenue):,} ₽"
            ),
            "action": {"type": "stats", "products": products, "orders": orders, "revenue": int(revenue)},
        }

    async def _handle_help(self, message: str, match: re.Match) -> dict:
        return {
            "success": True,
            "message": (
                "🤖 Я могу помочь с управлением магазина:\n\n"
                "🎨 'Смени тему на cyber' — изменить дизайн\n"
                "🏷️ 'Создай промокод SALE20 на 20%' — добавить промокод\n"
                "📣 'Создай баннер Летняя распродажа' — добавить баннер\n"
                "✅ 'Включи отзывы' — активировать функцию\n"
                "❌ 'Выключи промокоды' — отключить функцию\n"
                "📝 'Название магазина = TechShop' — изменить название\n"
                "📊 'Покажи статистику' — вывод статистики\n"
            ),
            "intent": "help",
        }


async def process_ai_message(
    session: AsyncSession,
    tenant_id: int,
    message: str,
) -> dict:
    """Process AI chat message."""
    assistant = AIAssistant(session, tenant_id)
    return await assistant.process_message(message)
