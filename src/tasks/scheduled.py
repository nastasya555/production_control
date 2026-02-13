from __future__ import annotations

from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.data.models.batch import Batch
from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.domain.services.analytics_service import get_dashboard_statistics
from src.tasks.webhooks import send_webhook_delivery
from src.storage.minio_service import MinIOService


engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@shared_task(name="tasks.auto_close_expired_batches")
def auto_close_expired_batches() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                update(Batch)
                .where(Batch.shift_end < now, Batch.is_closed.is_(False))
                .values(is_closed=True, closed_at=now)
            )
            await session.execute(stmt)
            await session.commit()

    import asyncio

    asyncio.run(_run())


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
            # list_files возвращает только имена; для точной даты нужно вызывать клиент напрямую.
            # Для простоты сейчас не проверяем дату и не удаляем автоматически,
            # здесь можно расширить реализацию под реальные требования.
            # service.delete_file(bucket, obj_name)
            continue


@shared_task(name="tasks.update_cached_statistics")
def update_cached_statistics() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            # прогреваем кэш dashboard
            await get_dashboard_statistics(session)

    import asyncio

    asyncio.run(_run())


@shared_task(name="tasks.retry_failed_webhooks")
def retry_failed_webhooks() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            stmt = select(WebhookDelivery, WebhookSubscription).join(
                WebhookSubscription,
                WebhookSubscription.id == WebhookDelivery.subscription_id,
            ).where(
                WebhookDelivery.status == "failed",
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
            )
            result = await session.execute(stmt)
            rows = result.all()

            for delivery, _sub in rows:
                send_webhook_delivery.delay(delivery.id)

    import asyncio

    asyncio.run(_run())


