from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.work_center import WorkCenter
from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.product_repository import ProductRepository
from src.data.repositories.work_center_repository import WorkCenterRepository
from src.core.cache import get_redis, delete_pattern


class BatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.batch_repo = BatchRepository(session)
        self.product_repo = ProductRepository(session)
        self.work_center_repo = WorkCenterRepository(session)

    async def create_batches(self, items: Sequence[dict]) -> Iterable[Batch]:
        """
        Принимает список словарей с русскими полями из 1С, создаёт нужные WorkCenter и Batch.
        """
        created: list[Batch] = []
        for data in items:
            wc_identifier: str = data["ИдентификаторРЦ"]
            work_center = await self.work_center_repo.get_by_identifier(wc_identifier)
            if work_center is None:
                work_center = await self.work_center_repo.create(
                    {
                        "identifier": wc_identifier,
                        "name": data.get("РабочийЦентр", wc_identifier),
                    }
                )

            # нормализуем datetime без таймзоны для PostgreSQL (TIMESTAMP WITHOUT TIME ZONE)
            shift_start = data["ДатаВремяНачалаСмены"]
            shift_end = data["ДатаВремяОкончанияСмены"]
            if isinstance(shift_start, datetime) and shift_start.tzinfo is not None:
                shift_start = shift_start.replace(tzinfo=None)
            if isinstance(shift_end, datetime) and shift_end.tzinfo is not None:
                shift_end = shift_end.replace(tzinfo=None)

            batch = await self.batch_repo.create(
                {
                    "is_closed": data.get("СтатусЗакрытия", False),
                    "task_description": data["ПредставлениеЗаданияНаСмену"],
                    "work_center_id": work_center.id,
                    "shift": data["Смена"],
                    "team": data["Бригада"],
                    "batch_number": data["НомерПартии"],
                    "batch_date": data["ДатаПартии"],
                    "nomenclature": data["Номенклатура"],
                    "ekn_code": data["КодЕКН"],
                    "shift_start": shift_start,
                    "shift_end": shift_end,
                }
            )
            created.append(batch)

        await self.session.commit()
        # Инвалидация кэша аналитики
        redis = get_redis()
        await redis.delete("dashboard_stats")
        await delete_pattern("batch_statistics*")
        await delete_pattern("compare_batches*")
        return created

    async def update_batch_status(self, batch: Batch, *, is_closed: bool | None = None, **updates: object) -> Batch:
        data: dict[str, object] = dict(updates)
        if is_closed is not None and is_closed != batch.is_closed:
            data["is_closed"] = is_closed
            data["closed_at"] = datetime.utcnow() if is_closed else None
        updated = await self.batch_repo.update(batch, data)
        await self.session.commit()
        redis = get_redis()
        await redis.delete("dashboard_stats")
        await delete_pattern("batch_statistics*")
        await delete_pattern("compare_batches*")
        return updated

    async def aggregate_product(self, batch: Batch, code: str) -> Product:
        products = await self.product_repo.get_by_codes(batch.id, [code])
        if products:
            product = products[0]
        else:
            product = await self.product_repo.create({"batch_id": batch.id, "unique_code": code})

        if not product.is_aggregated:
            product = await self.product_repo.update(
                product,
                {
                    "is_aggregated": True,
                    "aggregated_at": datetime.utcnow(),
                },
            )
        await self.session.commit()
        redis = get_redis()
        await redis.delete("dashboard_stats")
        await delete_pattern("batch_statistics*")
        await delete_pattern("compare_batches*")
        return product



