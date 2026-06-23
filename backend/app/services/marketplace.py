"""Интеграция с маркетплейсами: Wildberries, Ozon."""
import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger("myshop.marketplace")


class MarketplaceExporter(ABC):
    """Базовый класс для экспорта на маркетплейсы."""

    @abstractmethod
    async def sync_products(self, products: list[dict]) -> dict:
        """Синхронизировать товары."""
        ...

    @abstractmethod
    async def get_orders(self) -> list[dict]:
        """Получить заказы."""
        ...


class WildberriesExporter(MarketplaceExporter):
    """Экспорт на Wildberries."""

    BASE_URL = "https://api.wildberries.ru"

    def __init__(self, api_token: str):
        self.headers = {"Authorization": api_token}

    async def sync_products(self, products: list[dict]) -> dict:
        """Выгрузить товары на WB."""
        uploaded = 0
        errors = []

        async with httpx.AsyncClient() as client:
            for product in products:
                try:
                    payload = {
                        "supplierArticle": product.get("sku", f"MYSHOP-{product['id']}"),
                        "title": product["name"],
                        "price": int(product["price"] * 0.85),  # WB берёт ~15%
                        "category": product.get("wb_category", "Электроника"),
                        "description": product.get("description", ""),
                        "images": [product.get("image", "")],
                    }
                    resp = await client.post(
                        f"{self.BASE_URL}/content/v2/cards/create",
                        json=[payload],
                        headers=self.headers,
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        uploaded += 1
                    else:
                        errors.append({"product": product["name"], "error": resp.text})
                except Exception as e:
                    errors.append({"product": product["name"], "error": str(e)})

        return {"uploaded": uploaded, "errors": errors}

    async def get_orders(self) -> list[dict]:
        """Получить заказы с WB."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/api/v5/supplier/orders",
                headers=self.headers,
                params={"flag": 0},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
        return []


class OzonExporter(MarketplaceExporter):
    """Экспорт на Ozon."""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        self.headers = {
            "Client-Id": client_id,
            "Api-Key": api_key,
        }

    async def sync_products(self, products: list[dict]) -> dict:
        """Выгрузить товары на Ozon."""
        uploaded = 0
        errors = []

        async with httpx.AsyncClient() as client:
            items = []
            for product in products:
                items.append({
                    "name": product["name"],
                    "offer_id": f"MYSHOP-{product['id']}",
                    "price": str(int(product["price"] * 0.9)),  # Ozon берёт ~10%
                    "vat": "0",
                    "images": [product.get("image", "")],
                    "description": product.get("description", ""),
                })

            try:
                resp = await client.post(
                    f"{self.BASE_URL}/v2/product/import",
                    json={"items": items},
                    headers=self.headers,
                    timeout=60,
                )
                if resp.status_code == 200:
                    uploaded = len(items)
                else:
                    errors.append({"error": resp.text})
            except Exception as e:
                errors.append({"error": str(e)})

        return {"uploaded": uploaded, "errors": errors}

    async def get_orders(self) -> list[dict]:
        """Получить заказы с Ozon."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/v3/posting/fbs/list",
                json={"filter": {"status": "awaiting_packaging"}, "limit": 50},
                headers=self.headers,
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("result", {}).get("postings", [])
        return []


# Реестр экспортеров
EXPORTERS = {
    "wildberries": WildberriesExporter,
    "ozon": OzonExporter,
}
