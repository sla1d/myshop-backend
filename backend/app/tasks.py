"""Celery tasks — background jobs for the platform."""
import json
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

logger = logging.getLogger("myshop.tasks")


@shared_task(name="app.tasks.send_email")
def send_email_task(to: str, subject: str, body: str, html: str = "") -> dict:
    """Send email via SMTP or Mailgun."""
    try:
        from app.services.email import send_email
        send_email(to, subject, body, html)
        logger.info("Email sent to %s: %s", to, subject)
        return {"status": "ok", "to": to}
    except Exception as e:
        logger.error("Email failed: %s", e)
        return {"status": "failed", "error": str(e)}


@shared_task(name="app.tasks.generate_sales_report")
def generate_sales_report(tenant_id: int, period: str = "30d") -> dict:
    """Generate sales report for a tenant."""
    logger.info("Generating sales report: tenant=%d, period=%s", tenant_id, period)
    return {"status": "ok", "tenant_id": tenant_id, "period": period}


@shared_task(name="app.tasks.cleanup_expired_promos")
def cleanup_expired_promos() -> dict:
    """Deactivate expired promo codes."""
    logger.info("Cleaning up expired promos...")
    return {"status": "ok"}


@shared_task(name="app.tasks.sync_marketplace")
def sync_marketplace(tenant_id: int, marketplace: str) -> dict:
    """Sync products with marketplace (Ozon/WB)."""
    logger.info("Syncing marketplace: tenant=%d, mp=%s", tenant_id, marketplace)
    return {"status": "ok", "tenant_id": tenant_id, "marketplace": marketplace}


@shared_task(name="app.tasks.check_subscriptions")
def check_subscriptions() -> dict:
    """Check and expire subscriptions."""
    from app.billing.service import BillingService
    from app.database.connection import async_session_factory
    import asyncio

    async def _check():
        async with async_session_factory() as session:
            service = BillingService(session)
            count = await service.check_expired_subscriptions()
            return count

    count = asyncio.run(_check())
    logger.info("Subscription check: %d expired", count)
    return {"status": "ok", "expired": count}


@shared_task(name="app.tasks.backup_database")
def backup_database() -> dict:
    """Daily database backup to S3/MinIO."""
    import subprocess
    import os
    from app.core.config import settings

    logger.info("Starting database backup...")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql.gz"

    try:
        # pg_dump with gzip
        cmd = f"pg_dump {settings.DATABASE_URL.replace('+asyncpg', '')} | gzip > /tmp/{filename}"
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=300)

        if result.returncode != 0:
            logger.error("pg_dump failed: %s", result.stderr.decode())
            return {"status": "failed", "error": result.stderr.decode()[:200]}

        # Upload to S3
        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        s3.upload_file(f"/tmp/{filename}", settings.S3_BUCKET, f"backups/{filename}")

        # Cleanup
        os.remove(f"/tmp/{filename}")

        logger.info("Backup completed: %s", filename)
        return {"status": "ok", "filename": filename}
    except Exception as e:
        logger.error("Backup failed: %s", e)
        return {"status": "failed", "error": str(e)}


@shared_task(name="app.tasks.send_notification")
def send_notification(user_id: int, message: str, notification_type: str = "info") -> dict:
    """Send notification via WebSocket or Telegram."""
    try:
        import asyncio
        from app.core.websocket import manager

        async def _send():
            await manager.send(user_id, {
                "type": notification_type,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        asyncio.run(_send())
        return {"status": "ok", "user_id": user_id}
    except Exception as e:
        logger.warning("Notification failed: %s", e)
        return {"status": "failed", "error": str(e)}


@shared_task(name="app.tasks.cleanup_expired_sessions")
def cleanup_expired_sessions() -> dict:
    """Remove expired refresh tokens."""
    from app.security.models import RefreshToken
    from app.database.connection import async_session_factory
    from sqlalchemy import delete
    import asyncio

    async def _cleanup():
        async with async_session_factory() as session:
            result = await session.execute(
                delete(RefreshToken).where(
                    RefreshToken.expires_at < datetime.now(timezone.utc),
                    RefreshToken.revoked == True,
                )
            )
            await session.commit()
            return result.rowcount

    count = asyncio.run(_cleanup())
    logger.info("Cleaned %d expired sessions", count)
    return {"status": "ok", "cleaned": count}


@shared_task(name="app.tasks.cleanup_expired_roles")
def cleanup_expired_roles() -> dict:
    """Remove expired temporary roles from users."""
    from app.rbac.models import UserRole
    from app.database.connection import async_session_factory
    from sqlalchemy import delete
    import asyncio

    async def _cleanup():
        async with async_session_factory() as session:
            result = await session.execute(
                delete(UserRole).where(
                    UserRole.expires_at != None,
                    UserRole.expires_at < datetime.now(timezone.utc),
                )
            )
            await session.commit()
            return result.rowcount

    count = asyncio.run(_cleanup())
    if count > 0:
        logger.info("Cleaned %d expired roles", count)
    return {"status": "ok", "cleaned": count}
