from __future__ import annotations

from typing import Sequence

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.core.config import settings
from src.core.database import Base
from src.data.models.product import Product


engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@shared_task(bind=True, max_retries=3)
def aggregate_products_batch(self, batch_id: int, unique_codes: Sequence[str], user_id: int | None = None) -> dict:
    """
    Асинхронная массовая агрегация продукции.
    """

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            from src.domain.services.batch_service import BatchService

            service = BatchService(session)
            total = len(unique_codes)
            aggregated = 0
            errors: list[dict] = []

            for idx, code in enumerate(unique_codes, start=1):
                try:
                    await service.aggregate_product(batch_id=batch_id, code=code)
                    aggregated += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append({"code": code, "reason": str(exc)})

                if idx % 10 == 0 or idx == total:
                    self.update_state(
                        state="PROGRESS",
                        meta={"current": idx, "total": total, "progress": round(idx / total * 100, 2)},
                    )

            return {
                "success": len(errors) == 0,
                "total": total,
                "aggregated": aggregated,
                "failed": len(errors),
                "errors": errors,
            }

    import asyncio

    return asyncio.run(_run())



