from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

import httpx
from celery import shared_task
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.data.models.batch import Batch
from src.data.models.work_center import WorkCenter
from src.data.models.webhook import WebhookSubscription, WebhookDelivery
from src.tasks.base import DatabaseTask
from src.utils.excel_parser import parse_batches_file
from src.tasks.webhooks import send_webhook_delivery


logger = logging.getLogger(__name__)


@shared_task(bind=True, base=DatabaseTask, max_retries=1)
def import_batches_from_file(self, file_url: str, user_id: int) -> dict:
    """
    Импорт партий из Excel/CSV файла по presigned URL из MinIO.
    """
    session: Session = self.get_session()  # type: ignore[attr-defined]

    try:
        # Скачиваем файл по URL во временную директорию
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "batches_import")
            with httpx.Client() as client:
                resp = client.get(file_url)
                resp.raise_for_status()
                with open(filename, "wb") as f:
                    f.write(resp.content)

            items, errors = parse_batches_file(filename)

        total_rows = len(items)
        created = 0
        skipped = 0

        for idx, item in enumerate(items, start=1):
            try:
                wc_identifier = item["ИдентификаторРЦ"]
                work_center = (
                    session.query(WorkCenter)
                    .filter(WorkCenter.identifier == wc_identifier)
                    .one_or_none()
                )
                if work_center is None:
                    work_center = WorkCenter(
                        identifier=wc_identifier,
                        name=item.get("РабочийЦентр") or wc_identifier,
                    )
                    session.add(work_center)
                    session.flush()

                batch = Batch(
                    is_closed=item.get("СтатусЗакрытия", False),
                    task_description=item["ПредставлениеЗаданияНаСмену"],
                    work_center_id=work_center.id,
                    shift=item["Смена"],
                    team=item["Бригада"],
                    batch_number=item["НомерПартии"],
                    batch_date=item["ДатаПартии"],
                    nomenclature=item["Номенклатура"],
                    ekn_code=item.get("КодЕКН", ""),
                    shift_start=item["ДатаВремяНачалаСмены"],
                    shift_end=item["ДатаВремяОкончанияСмены"],
                )
                session.add(batch)
                session.commit()
                created += 1
            except IntegrityError as exc:
                session.rollback()
                skipped += 1
                logger.error(
                    "Integrity error during batch import",
                    exc_info=True,
                    extra={"row": idx},
                )
                errors.append(
                    {
                        "row": idx,
                        "error_type": exc.__class__.__name__,
                        "error": "duplicate batch or constraint error",
                    }
                )
            except Exception as exc:
                session.rollback()
                skipped += 1
                logger.critical(
                    "Unexpected error in import_batches_from_file",
                    exc_info=True,
                    extra={"row": idx},
                )
                raise

            if idx % 10 == 0 or idx == total_rows:
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": idx,
                        "total": total_rows,
                        "created": created,
                        "skipped": skipped,
                    },
                )

        result = {
            "success": True,
            "total_rows": total_rows,
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }

        # webhook import_completed
        payload = {
            "total_rows": total_rows,
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }
        subs = (
            session.query(WebhookSubscription)
            .filter(
                WebhookSubscription.is_active.is_(True),
                WebhookSubscription.events.any("import_completed"),
            )
            .all()
        )
        for sub in subs:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type="import_completed",
                payload=payload,
                status="pending",
            )
            session.add(delivery)
            session.flush()
            send_webhook_delivery.delay(delivery.id)
        session.commit()

        return result
    finally:
        session.close()
