from __future__ import annotations

import os
import tempfile
from typing import Any

import httpx
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.domain.services.batch_service import BatchService
from src.utils.excel_parser import parse_batches_file


engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@shared_task(bind=True, max_retries=1)
def import_batches_from_file(self, file_url: str, user_id: int) -> dict:
    """
    Импорт партий из Excel/CSV файла по presigned URL из MinIO.
    """

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            # Скачиваем файл по URL во временную директорию
            with tempfile.TemporaryDirectory() as tmpdir:
                filename = os.path.join(tmpdir, "batches_import")
                async with httpx.AsyncClient() as client:
                    resp = await client.get(file_url)
                    resp.raise_for_status()
                    with open(filename, "wb") as f:
                        f.write(resp.content)

                items, errors = parse_batches_file(filename)

                service = BatchService(session)
                total_rows = len(items)
                created = 0
                skipped = 0

                for idx, item in enumerate(items, start=1):
                    try:
                        await service.create_batches([item])
                        created += 1
                    except Exception as exc:  # noqa: BLE001
                        skipped += 1
                        errors.append({"row": idx, "error": str(exc)})

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

                return {
                    "success": True,
                    "total_rows": total_rows,
                    "created": created,
                    "skipped": skipped,
                    "errors": errors,
                }

    import asyncio

    return asyncio.run(_run())



