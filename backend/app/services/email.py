import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"
_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def render_template(template_name: str, **kwargs) -> str:
    tpl = _env.get_template(template_name)
    return tpl.render(**kwargs)


def send_order_confirmation_email(order_id: int, username: str, email: str, total: int, address: str, discount: int = 0, cashback: int = 0):
    """Отправить email подтверждения заказа (sync для Celery)."""
    html = render_template(
        "order_confirmation.html",
        order_id=order_id,
        username=username,
        total=f"{total:,}".replace(",", " "),
        address=address,
        discount=f"{discount:,}".replace(",", " ") if discount else None,
        cashback=cashback or None,
    )
    logger.info("[Email] Order confirmation → %s (order #%d)", email, order_id)
    return {"status": "sent", "to": email, "template": "order_confirmation"}


def send_order_status_email(order_id: int, username: str, email: str, status: str, tracking_number: str = None):
    """Отправить email об обновлении статуса."""
    html = render_template(
        "order_status_update.html",
        order_id=order_id,
        username=username,
        status=status,
        tracking_number=tracking_number,
    )
    logger.info("[Email] Status update → %s (order #%d, status=%s)", email, order_id, status)
    return {"status": "sent", "to": email, "template": "order_status_update"}


def send_welcome_email(username: str, email: str, store_name: str = "MyShop", store_url: str = "https://myshop.com", cashback: int = 0):
    """Отправить приветственный email."""
    html = render_template(
        "welcome.html",
        username=username,
        store_name=store_name,
        store_url=store_url,
        cashback=cashback or None,
    )
    logger.info("[Email] Welcome → %s", email)
    return {"status": "sent", "to": email, "template": "welcome"}


def send_shipping_email(order_id: int, username: str, email: str, address: str, tracking_number: str = None, carrier: str = None, estimated_delivery: str = None, tracking_url: str = None, store_name: str = "MyShop"):
    """Отправить email об отправке заказа."""
    html = render_template(
        "shipping.html",
        order_id=order_id,
        username=username,
        address=address,
        tracking_number=tracking_number,
        carrier=carrier,
        estimated_delivery=estimated_delivery,
        tracking_url=tracking_url,
        store_name=store_name,
    )
    logger.info("[Email] Shipping → %s (order #%d)", email, order_id)
    return {"status": "sent", "to": email, "template": "shipping"}


def send_promo_email(username: str, email: str, promo_name: str, promo_code: str, promo_description: str = "", discount_percent: int = None, discount_amount: int = None, valid_until: str = None, store_name: str = "MyShop", store_url: str = "https://myshop.com"):
    """Отправить промо email."""
    html = render_template(
        "promo.html",
        username=username,
        promo_name=promo_name,
        promo_code=promo_code,
        promo_description=promo_description,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        valid_until=valid_until,
        store_name=store_name,
        store_url=store_url,
    )
    logger.info("[Email] Promo → %s (code=%s)", email, promo_code)
    return {"status": "sent", "to": email, "template": "promo"}
