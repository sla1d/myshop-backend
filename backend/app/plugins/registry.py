"""Plugin registry — available plugins for the platform."""
import logging

logger = logging.getLogger("myshop.plugins")


class PluginDefinition:
    """Defines a plugin that can be installed in a tenant store."""

    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        version: str = "1.0.0",
        category: str = "other",
        requires: list[str] | None = None,
        config_schema: dict | None = None,
    ):
        self.key = key
        self.name = name
        self.description = description
        self.version = version
        self.category = category
        self.requires = requires or []
        self.config_schema = config_schema or {}

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "requires": self.requires,
            "config_schema": self.config_schema,
        }


# ─── Available Plugins ───────────────────────────────
AVAILABLE_PLUGINS: dict[str, PluginDefinition] = {}


def _register(plugins: list[PluginDefinition]) -> None:
    for p in plugins:
        AVAILABLE_PLUGINS[p.key] = p


_register([
    PluginDefinition(
        key="telegram_bot",
        name="Telegram Bot",
        description="Уведомления о заказах в Telegram, чат-бот для покупателей",
        category="messaging",
        config_schema={
            "bot_token": {"type": "string", "required": True, "label": "Bot Token"},
            "chat_id": {"type": "string", "required": True, "label": "Chat ID"},
            "notify_orders": {"type": "bool", "default": True, "label": "Уведомлять о заказах"},
            "notify_payments": {"type": "bool", "default": True, "label": "Уведомлять об оплатах"},
        },
    ),
    PluginDefinition(
        key="whatsapp",
        name="WhatsApp Business",
        description="Отправка уведомлений о заказах через WhatsApp",
        category="messaging",
        config_schema={
            "phone_number_id": {"type": "string", "required": True, "label": "Phone Number ID"},
            "access_token": {"type": "string", "required": True, "label": "Access Token"},
            "verify_token": {"type": "string", "required": True, "label": "Verify Token"},
        },
    ),
    PluginDefinition(
        key="sms",
        name="SMS Уведомления",
        description="СМС-уведомления о статусе заказа через SMS.ru / Twilio",
        category="messaging",
        config_schema={
            "provider": {"type": "select", "options": ["sms_ru", "twilio", "textbelt"], "label": "Провайдер"},
            "api_key": {"type": "string", "required": True, "label": "API Key"},
            "sender": {"type": "string", "required": False, "label": "Имя отправителя"},
        },
    ),
    PluginDefinition(
        key="email_marketing",
        name="Email Рассылки",
        description="Автоматические email-рассылки: приветствие, брошенная корзина, промо",
        category="marketing",
        config_schema={
            "smtp_host": {"type": "string", "required": True, "label": "SMTP Host"},
            "smtp_port": {"type": "int", "default": 587, "label": "SMTP Port"},
            "smtp_user": {"type": "string", "required": True, "label": "SMTP User"},
            "smtp_password": {"type": "string", "required": True, "label": "SMTP Password"},
            "from_email": {"type": "string", "required": True, "label": "From Email"},
            "from_name": {"type": "string", "required": True, "label": "From Name"},
        },
    ),
    PluginDefinition(
        key="yookassa",
        name="ЮKassa",
        description="Приём платежей через ЮKassa (банковские карты, СБП,��联)",
        category="payments",
        config_schema={
            "shop_id": {"type": "string", "required": True, "label": "Shop ID"},
            "secret_key": {"type": "string", "required": True, "label": "Secret Key"},
            "return_url": {"type": "string", "required": False, "label": "Return URL"},
        },
    ),
    PluginDefinition(
        key="cdek",
        name="СДЭК Доставка",
        description="Расчёт стоимости доставки и отслеживание через СДЭК",
        category="delivery",
        config_schema={
            "client_id": {"type": "string", "required": True, "label": "Client ID"},
            "client_secret": {"type": "string", "required": True, "label": "Client Secret"},
            "default_city_from": {"type": "string", "required": False, "label": "Город отправления"},
        },
    ),
    PluginDefinition(
        key="wildberries",
        name="Wildberries",
        description="Синхронизация товаров и заказов с Wildberries",
        category="marketplace",
        config_schema={
            "api_key": {"type": "string", "required": True, "label": "API Key"},
            "sync_products": {"type": "bool", "default": True, "label": "Синхронизировать товары"},
            "sync_orders": {"type": "bool", "default": True, "label": "Синхронизировать заказы"},
        },
    ),
    PluginDefinition(
        key="ozon",
        name="Ozon",
        description="Синхронизация товаров и заказов с Ozon",
        category="marketplace",
        config_schema={
            "client_id": {"type": "string", "required": True, "label": "Client ID"},
            "api_key": {"type": "string", "required": True, "label": "API Key"},
        },
    ),
    PluginDefinition(
        key="ai_assistant",
        name="ИИ-Помощник",
        description="AI-ассистент для генерации описаний, баннеров, аналитики",
        category="ai",
        config_schema={
            "model": {"type": "select", "options": ["gpt-4", "gpt-3.5-turbo", "claude"], "label": "Модель"},
            "max_tokens": {"type": "int", "default": 1000, "label": "Max Tokens"},
        },
    ),
    PluginDefinition(
        key="google_analytics",
        name="Google Analytics",
        description="Подключение Google Analytics 4 для отслеживания",
        category="analytics",
        config_schema={
            "measurement_id": {"type": "string", "required": True, "label": "Measurement ID"},
            "stream_id": {"type": "string", "required": False, "label": "Stream ID"},
        },
    ),
])


def get_plugin(key: str) -> PluginDefinition | None:
    return AVAILABLE_PLUGINS.get(key)


def list_plugins(category: str | None = None) -> list[dict]:
    plugins = AVAILABLE_PLUGINS.values()
    if category:
        plugins = [p for p in plugins if p.category == category]
    return [p.to_dict() for p in plugins]
