"""SMS integration — send order notifications via SMS.ru / Twilio / Textbelt."""
import logging
from typing import Any

import httpx

logger = logging.getLogger("myshop.integrations.sms")


class SMSProvider:
    """Base class for SMS providers."""

    async def send(self, phone: str, text: str) -> dict[str, Any]:
        raise NotImplementedError


class SMSRuProvider(SMSProvider):
    """SMS.ru provider."""

    def __init__(self, api_key: str, sender: str = ""):
        self.api_key = api_key
        self.sender = sender

    async def send(self, phone: str, text: str) -> dict[str, Any]:
        url = "https://sms.ru/sms/send"
        params = {
            "api_id": self.api_key,
            "to": phone,
            "msg": text,
            "json": 1,
        }
        if self.sender:
            params["from"] = self.sender
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            return resp.json()


class TwilioProvider(SMSProvider):
    """Twilio SMS provider."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send(self, phone: str, text: str) -> dict[str, Any]:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        import base64
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        data = {"To": phone, "From": self.from_number, "Body": text}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, data=data,
                headers={"Authorization": f"Basic {auth}"},
                timeout=10,
            )
            return resp.json()


class TextbeltProvider(SMSProvider):
    """Textbelt provider (free tier: 1 SMS/day)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def send(self, phone: str, text: str) -> dict[str, Any]:
        url = "https://textbelt.com/text"
        data = {"phone": phone, "message": text, "key": self.api_key}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data, timeout=10)
            return resp.json()


def create_sms_provider(provider: str, **kwargs) -> SMSProvider:
    providers = {
        "sms_ru": lambda: SMSRuProvider(kwargs["api_key"], kwargs.get("sender", "")),
        "twilio": lambda: TwilioProvider(
            kwargs["account_sid"], kwargs["auth_token"], kwargs["from_number"]
        ),
        "textbelt": lambda: TextbeltProvider(kwargs["api_key"]),
    }
    factory = providers.get(provider)
    if not factory:
        raise ValueError(f"Unknown SMS provider: {provider}")
    return factory()


async def send_order_sms(
    provider: SMSProvider, phone: str, order_id: int, status: str
) -> dict[str, Any]:
    """Send order status SMS."""
    status_map = {
        "processing": f"Ваш заказ #{order_id} обрабатывается",
        "shipped": f"Ваш заказ #{order_id} отправлен",
        "delivered": f"Ваш заказ #{order_id} доставлен",
        "cancelled": f"Ваш заказ #{order_id} отменён",
    }
    text = status_map.get(status, f"Заказ #{order_id}: {status}")
    return await provider.send(phone, text)
