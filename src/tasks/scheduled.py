from __future__ import annotations

from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.data.models.batch import Batch
from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.domain.services.analytics_service import get_dashboard_statistics
from src.tasks.base import DatabaseTask
from src.tasks.webhooks import send_webhook_delivery
from src.storage.minio_service import MinIOService


@shared_task(name="tasks.auto_close_expired_batches", bind=True, base=DatabaseTask)
def auto_close_expired_batches(self) -> None:
    session: Session = self.get_session()  # type: ignore[attr-defined]
    try:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Batch)
            .where(Batch.shift_end < now, Batch.is_closed.is_(False))
            .values(is_closed=True, closed_at=now)
        )
        session.execute(stmt)
        session.commit()
    finally:
        session.close()


@shared_task(name="tasks.cleanup_old_files")
def cleanup_old_files() -> None:
    """
    Удаляет файлы старше 30 дней из MinIO в бакетах reports/exports/imports.
    """
    service = MinIOService()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    buckets = ["reports", "exports", "imports"]

    for bucket in buckets:
        for obj_name in service.list_files(bucket):
            # TODO: получить метаданные объекта и сравнивать с cutoff
            # service.delete_file(bucket, obj_name) при необходимости
            continue


@shared_task(name="tasks.update_cached_statistics", bind=True, base=DatabaseTask)
def update_cached_statistics(self) -> None:
    # Прогрев кэша: проще дернуть API (оно само положит в Redis).
    # Это безопаснее, чем дублировать расчеты в sync-режиме.
    import httpx

    with httpx.Client(timeout=10) as client:
        # внутри docker-compose api доступен по имени сервиса "api"
        client.get("http://api:8000/api/v1/analytics/dashboard")


@shared_task(name="tasks.retry_failed_webhooks", bind=True, base=DatabaseTask)
def retry_failed_webhooks(self) -> None:
    session: Session = self.get_session()  # type: ignore[attr-defined]
    try:
        stmt = (
            select(WebhookDelivery, WebhookSubscription)
            .join(
                WebhookSubscription,
                WebhookSubscription.id == WebhookDelivery.subscription_id,
            )
            .where(
                WebhookDelivery.status == "failed",
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
            )
        )
        rows = session.execute(stmt).all()

        for delivery, _sub in rows:
            send_webhook_delivery.delay(delivery.id)
    finally:
        session.close()

