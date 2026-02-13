from __future__ import annotations

import os
import tempfile
from typing import Any

from celery import shared_task
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.data.models.batch import Batch
from src.storage.minio_service import MinIOService
from src.utils.excel_generator import export_batches_to_csv, export_batches_to_excel


engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@shared_task
def export_batches_to_file(filters: dict[str, Any], format: str = "excel") -> dict:
    """
    Экспорт списка партий в Excel/CSV файл и загрузка в MinIO.
    """

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            conditions = []
            if "is_closed" in filters and filters["is_closed"] is not None:
                conditions.append(Batch.is_closed == bool(filters["is_closed"]))
            if "date_from" in filters:
                conditions.append(Batch.batch_date >= filters["date_from"])
            if "date_to" in filters:
                conditions.append(Batch.batch_date <= filters["date_to"])

            stmt = select(Batch)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            result = await session.execute(stmt)
            batches = result.scalars().all()

            rows: list[dict[str, Any]] = []
            for b in batches:
                rows.append(
                    {
                        "id": b.id,
                        "batch_number": b.batch_number,
                        "batch_date": b.batch_date,
                        "is_closed": b.is_closed,
                        "work_center_id": b.work_center_id,
                        "shift": b.shift,
                        "team": b.team,
                        "nomenclature": b.nomenclature,
                        "ekn_code": b.ekn_code,
                    }
                )

            suffix = ".xlsx" if format == "excel" else ".csv"
            filename = "batches_export" + suffix

            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, filename)
                if format == "excel":
                    export_batches_to_excel(rows, path)
                else:
                    export_batches_to_csv(rows, path)

                storage = MinIOService()
                url = storage.upload_file(bucket="exports", file_path=path, object_name=filename)

            return {
                "success": True,
                "file_url": url,
                "total_batches": len(rows),
            }

    import asyncio

    return asyncio.run(_run())


