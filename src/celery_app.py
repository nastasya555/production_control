from celery import Celery
from celery.schedules import crontab

from src.core.config import settings


celery_app = Celery(
    "production_control",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=60 * 30,
    result_expires=60 * 60 * 24,
)

# Автообнаружение задач в пакете src.tasks
celery_app.autodiscover_tasks(["src.tasks"])

# Расписание задач Celery Beat
celery_app.conf.beat_schedule = {
    "auto-close-expired-batches": {
        "task": "tasks.auto_close_expired_batches",
        "schedule": crontab(hour=1, minute=0),
    },
    "cleanup-old-files": {
        "task": "tasks.cleanup_old_files",
        "schedule": crontab(hour=2, minute=0),
    },
    "update-statistics": {
        "task": "tasks.update_cached_statistics",
        "schedule": crontab(minute="*/5"),
    },
    "retry-failed-webhooks": {
        "task": "tasks.retry_failed_webhooks",
        "schedule": crontab(minute="*/15"),
    },
}





