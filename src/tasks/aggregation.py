from __future__ import annotations

from datetime import datetime
from typing import Sequence
import logging

from celery import shared_task
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.data.models.product import Product
from src.data.models.batch import Batch
from src.tasks.base import DatabaseTask


logger = logging.getLogger(__name__)

BATCH_SIZE = 100


@shared_task(bind=True, base=DatabaseTask, max_retries=3)
def aggregate_products_batch(self, batch_id: int, unique_codes: Sequence[str], user_id: int | None = None) -> dict:
    """
    Массовая агрегация продукции (синхронная задача Celery).
    """
    session: Session = self.get_session()  # type: ignore[attr-defined]

    try:
        batch = session.get(Batch, batch_id)
        if batch is None:
            raise ValueError("Batch not found")

        total = len(unique_codes)
        aggregated = 0
        errors: list[dict] = []

        for idx, code in enumerate(unique_codes, start=1):
            try:
                product = (
                    session.query(Product)
                    .filter(Product.batch_id == batch_id, Product.unique_code == code)
                    .with_for_update(of=Product, nowait=False)
                    .one_or_none()
                )

                if product is None:
                    product = Product(batch_id=batch_id, unique_code=code)
                    session.add(product)

                if not product.is_aggregated:
                    product.is_aggregated = True
                    product.aggregated_at = datetime.utcnow()

                aggregated += 1

                if idx % BATCH_SIZE == 0:
                    session.commit()

            except IntegrityError as exc:
                session.rollback()
                logger.error(
                    "Integrity error aggregating product",
                    exc_info=True,
                    extra={"batch_id": batch_id, "code": code},
                )
                errors.append(
                    {
                        "code": code,
                        "error_type": exc.__class__.__name__,
                        "reason": "duplicate or concurrent update",
                    }
                )
            except Exception as exc:
                session.rollback()
                logger.critical(
                    "Unexpected error in aggregate_products_batch",
                    exc_info=True,
                    extra={"batch_id": batch_id, "code": code},
                )
                raise

            if idx % 10 == 0 or idx == total:
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": idx,
                        "total": total,
                        "progress": round(idx / total * 100, 2),
                    },
                )

        # финальный commit, если остались незафиксированные изменения
        session.commit()

        return {
            "success": len(errors) == 0,
            "total": total,
            "aggregated": aggregated,
            "failed": len(errors),
            "errors": errors,
        }
    finally:
        session.close()

