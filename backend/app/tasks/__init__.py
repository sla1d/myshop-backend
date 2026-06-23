import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.send_order_notification")
def send_order_notification(self, order_id: int, user_email: str, total: int):
    """Отправить уведомление о заказе (имитация email)."""
    logger.info("📧 Отправка уведомления о заказе #%d на %s (сумма: %d ₽)", order_id, user_email, total)
    # В реальном проекте: SMTP / SendGrid / SES
    return {"status": "sent", "order_id": order_id, "email": user_email}


@celery_app.task(bind=True, name="tasks.send_promo_notification")
def send_promo_notification(self, user_emails: list[str], promo_code: str, discount: int):
    """Рассылка промокода пользователям (имитация)."""
    logger.info("📧 Рассылка промокода %s (-%d%%) на %d адресов", promo_code, discount, len(user_emails))
    return {"status": "sent", "count": len(user_emails)}


@celery_app.task(bind=True, name="tasks.generate_sales_report")
def generate_sales_report(self):
    """Сформировать отчёт о продажах (имитация)."""
    logger.info("📊 Формирование отчёта о продажах...")
    # В реальном проекте: запрос в БД + генерация PDF/CSV
    return {
        "status": "done",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_url": "/reports/sales_report.pdf",
    }


@celery_app.task(bind=True, name="tasks.cleanup_expired_promos")
def cleanup_expired_promos(self):
    """Деактивировать истёкшие промокоды (имитация)."""
    logger.info("🧹 Очистка истёкших промокодов...")
    return {"status": "done", "cleaned": 0}
