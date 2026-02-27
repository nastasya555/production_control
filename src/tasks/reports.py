from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.webhook import WebhookSubscription, WebhookDelivery
from src.storage.minio_service import MinIOService
from src.tasks.base import DatabaseTask
from src.tasks.webhooks import send_webhook_delivery
from src.utils.report_strategies import ReportFactory


@shared_task(bind=True, base=DatabaseTask, max_retries=3)
def generate_batch_report(self, batch_id: int, format: str = "excel", user_email: str | None = None) -> dict:
    """
    Генерация детального отчёта по партии (Excel/PDF) и загрузка в MinIO.
    """
    session: Session = self.get_session()  # type: ignore[attr-defined]

    try:
        stmt = (
            select(Batch)
            .options(selectinload(Batch.products), selectinload(Batch.work_center))
            .where(Batch.id == batch_id)
        )
        batch = session.execute(stmt).scalars().one_or_none()
        if batch is None:
            raise ValueError("Batch not found")

        products: list[Product] = list(batch.products)

        strategy = ReportFactory.get_strategy(format)
        suffix = strategy.file_extension
        filename = f"batch_{batch_id}_report{suffix}"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, filename)
            strategy.generate(batch, products, path)

            storage = MinIOService()
            url = storage.upload_file(bucket="reports", file_path=path, object_name=filename)
            file_size = os.path.getsize(path)

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        # создаём webhook события report_generated
        payload = {
            "batch_id": batch.id,
            "report_type": format,
            "file_url": url,
            "expires_at": expires_at.isoformat(),
        }
        subs = (
            session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.is_active.is_(True),
                WebhookSubscription.events.any("report_generated"),
            )
            .all()
        )
        for sub in subs:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type="report_generated",
                payload=payload,
                status="pending",
            )
            session.add(delivery)
            session.flush()
            send_webhook_delivery.delay(delivery.id)
        session.commit()

        return {
            "success": True,
            "file_url": url,
            "file_name": filename,
            "file_size": file_size,
            "expires_at": expires_at.isoformat(),
        }
    finally:
        session.close()



