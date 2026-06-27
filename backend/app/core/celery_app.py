from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "myshop",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    beat_schedule={
        "reset-demo-daily": {
            "task": "app.tasks.demo.reset_demo",
            "schedule": 86400.0,  # 24 часа
        },
        "cleanup-expired-roles": {
            "task": "app.tasks.cleanup_expired_roles",
            "schedule": 3600.0,  # каждый час
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
