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
