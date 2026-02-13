from __future__ import annotations

from datetime import date
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from src.api.v1.schemas.batch import BatchCreateItem, BatchRead, BatchUpdate
from src.api.v1.schemas.files import BatchReportRequest, BatchExportRequest
from src.core.database import get_db
from src.data.models.batch import Batch
from src.domain.services.batch_service import BatchService
from src.tasks.aggregation import aggregate_products_batch
from src.tasks.reports import generate_batch_report
from src.tasks.imports import import_batches_from_file
from src.tasks.exports import export_batches_to_file
from src.storage.minio_service import MinIOService


router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_batches(
    items: Sequence[BatchCreateItem],
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = BatchService(db)
    created = await service.create_batches([item.model_dump() for item in items])
    return {"created": [batch.id for batch in created]}


@router.get("/{batch_id}", response_model=BatchRead)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
) -> BatchRead:
    stmt = select(Batch).options(joinedload(Batch.products)).where(Batch.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalars().unique().one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch


@router.patch("/{batch_id}", response_model=BatchRead)
async def update_batch(
    batch_id: int,
    payload: BatchUpdate,
    db: AsyncSession = Depends(get_db),
) -> BatchRead:
    batch = await db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    service = BatchService(db)
    updated = await service.update_batch_status(batch, **payload.model_dump(exclude_unset=True))
    await db.refresh(updated)
    return updated


@router.get("", response_model=List[BatchRead])
async def list_batches(
    is_closed: bool | None = None,
    batch_number: int | None = None,
    batch_date: date | None = None,
    work_center_id: int | None = None,
    shift: str | None = None,
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> List[BatchRead]:
    service = BatchService(db)
    batches = await service.batch_repo.list_filtered(
        is_closed=is_closed,
        batch_number=batch_number,
        batch_date=batch_date,
        work_center_id=work_center_id,
        shift=shift,
        offset=offset,
        limit=min(limit, 100),
    )
    return list(batches)


@router.post("/{batch_id}/aggregate-async", status_code=status.HTTP_202_ACCEPTED)
async def aggregate_batch_async(
    batch_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    codes: list[str] = body.get("unique_codes") or []
    if not codes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unique_codes is required")

    if await db.get(Batch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    task = aggregate_products_batch.delay(batch_id=batch_id, unique_codes=codes)
    return {
        "task_id": task.id,
        "status": task.status,
        "message": "Aggregation task started",
    }


@router.post("/{batch_id}/reports", status_code=status.HTTP_202_ACCEPTED)
async def create_batch_report(
    batch_id: int,
    body: BatchReportRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await db.get(Batch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    task = generate_batch_report.delay(batch_id=batch_id, format=body.format, user_email=body.email)
    return {"task_id": task.id, "status": "PENDING"}


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_batches(
    file: UploadFile = File(...),
) -> dict:
    storage = MinIOService()
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, file.filename)
        with open(path, "wb") as f:
            f.write(await file.read())

        file_url = storage.upload_file(bucket="imports", file_path=path, object_name=file.filename)

    task = import_batches_from_file.delay(file_url=file_url, user_id=0)
    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": "File uploaded, import started",
    }


@router.post("/export", status_code=status.HTTP_202_ACCEPTED)
async def export_batches(
    body: BatchExportRequest,
) -> dict:
    task = export_batches_to_file.delay(filters=body.filters, format=body.format)
    return {"task_id": task.id}



