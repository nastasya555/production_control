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
from sqlalchemy.exc import IntegrityError


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
        try:
            for data in items:
                wc_identifier: str = data["work_center_identifier"]
                work_center = await self.work_center_repo.get_by_identifier(wc_identifier)
                if work_center is None:
                    work_center = await self.work_center_repo.create(
                        {
                            "identifier": wc_identifier,
                            "name": data.get("work_center_name", wc_identifier),
                        }
                    )

                # нормализуем datetime без таймзоны для PostgreSQL (TIMESTAMP WITHOUT TIME ZONE)
                shift_start = data["shift_start"]
                shift_end = data["shift_end"]
                if isinstance(shift_start, datetime) and shift_start.tzinfo is not None:
                    shift_start = shift_start.replace(tzinfo=None)
                if isinstance(shift_end, datetime) and shift_end.tzinfo is not None:
                    shift_end = shift_end.replace(tzinfo=None)

                batch = await self.batch_repo.create(
                    {
                        "is_closed": data.get("СтатусЗакрытия", False),
                        "task_description": data["task_description"],
                        "work_center_id": work_center.id,
                        "shift": data["shift"],
                        "team": data["team"],
                        "batch_number": data["batch_number"],
                        "batch_date": data["batch_date"],
                        "nomenclature": data["nomenclature"],
                        "ekn_code": data["ekn_code"],
                        "shift_start": shift_start,
                        "shift_end": shift_end,
                    }
                )
                created.append(batch)
        except Exception:
            await self.session.rollback()
            raise

        return created

    async def update_batch_status(self, batch: Batch, *, is_closed: bool | None = None, **updates: object) -> Batch:
        data: dict[str, object] = dict(updates)
        if is_closed is not None and is_closed != batch.is_closed:
            data["is_closed"] = is_closed
            data["closed_at"] = datetime.utcnow() if is_closed else None
        updated = await self.batch_repo.update(batch, data)
        return updated

    async def aggregate_product(self, batch: Batch, code: str) -> Product:
        products = await self.product_repo.get_by_codes(batch.id, [code])
        if products:
            product = products[0]
        else:
            try:
                product = await self.product_repo.create({"batch_id": batch.id, "unique_code": code})
            except IntegrityError:
                # кто-то уже создал параллельно
                products = await self.product_repo.get_by_codes(batch.id, [code])
                product = products[0]

        if not product.is_aggregated:
            product = await self.product_repo.update(
                product,
                {
                    "is_aggregated": True,
                    "aggregated_at": datetime.utcnow(),
                },
            )
        return product



