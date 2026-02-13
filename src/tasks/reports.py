from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from src.core.config import settings
from src.data.models.batch import Batch
from src.data.models.product import Product
from src.storage.minio_service import MinIOService
from src.utils.excel_generator import (
    generate_batch_report_excel,
    generate_batch_report_pdf,
)


engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@shared_task(bind=True, max_retries=3)
def generate_batch_report(self, batch_id: int, format: str = "excel", user_email: str | None = None) -> dict:
    """
    Генерация детального отчёта по партии (Excel/PDF) и загрузка в MinIO.
    """

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Batch)
                .options(selectinload(Batch.products), selectinload(Batch.work_center))
                .where(Batch.id == batch_id)
            )
            result = await session.execute(stmt)
            batch = result.scalar_one_or_none()
            if batch is None:
                raise ValueError("Batch not found")

            products: list[Product] = list(batch.products)

            suffix = ".xlsx" if format == "excel" else ".pdf"
            filename = f"batch_{batch_id}_report{suffix}"

            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, filename)
                if format == "excel":
                    generate_batch_report_excel(batch, products, path)
                else:
                    generate_batch_report_pdf(batch, products, path)

                storage = MinIOService()
                url = storage.upload_file(bucket="reports", file_path=path, object_name=filename)
                file_size = os.path.getsize(path)

            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            return {
                "success": True,
                "file_url": url,
                "file_name": filename,
                "file_size": file_size,
                "expires_at": expires_at.isoformat(),
            }

    import asyncio

    return asyncio.run(_run())



