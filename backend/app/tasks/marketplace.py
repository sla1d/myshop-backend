"""Celery задачи для маркетплейсов."""
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger("myshop.marketplace")


@celery_app.task(bind=True, name="tasks.sync_wildberries")
def sync_wildberries(self, tenant_id: int, api_token: str):
    """Синхронизация товаров с Wildberries."""
    import asyncio
    from app.services.marketplace import WildberriesExporter
    from app.database.connection import async_session_factory
    from app.models.product import Product
    from sqlalchemy import select

    async def _sync():
        exporter = WildberriesExporter(api_token)
        async with async_session_factory() as session:
            result = await session.execute(select(Product))
            products = [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "image": p.image,
                    "description": f"{p.brand} - {p.category}",
                }
                for p in result.scalars().all()
            ]
        return await exporter.sync_products(products)

    result = asyncio.run(_sync())
    logger.info("WB sync: uploaded=%d, errors=%d", result["uploaded"], len(result["errors"]))
    return result


@celery_app.task(bind=True, name="tasks.sync_ozon")
def sync_ozon(self, tenant_id: int, client_id: str, api_key: str):
    """Синхронизация товаров с Ozon."""
    import asyncio
    from app.services.marketplace import OzonExporter
    from app.database.connection import async_session_factory
    from app.models.product import Product
    from sqlalchemy import select

    async def _sync():
        exporter = OzonExporter(client_id, api_key)
        async with async_session_factory() as session:
            result = await session.execute(select(Product))
            products = [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "image": p.image,
                    "description": f"{p.brand} - {p.category}",
                }
                for p in result.scalars().all()
            ]
        return await exporter.sync_products(products)

    result = asyncio.run(_sync())
    logger.info("Ozon sync: uploaded=%d, errors=%d", result["uploaded"], len(result["errors"]))
    return result
