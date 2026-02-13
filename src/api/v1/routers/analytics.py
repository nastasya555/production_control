from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.analytics import (
    DashboardResponse,
    BatchStatisticsResponse,
    CompareBatchesRequest,
    CompareBatchesResponse,
)
from src.core.database import get_db
from src.domain.services.analytics_service import (
    get_dashboard_statistics,
    get_batch_statistics,
    compare_batches,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    data = await get_dashboard_statistics(db)
    return data  # type: ignore[return-value]


@router.get("/batches/{batch_id}/statistics", response_model=BatchStatisticsResponse)
async def batch_stats(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
) -> BatchStatisticsResponse:
    try:
        data = await get_batch_statistics(db, batch_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Batch not found")
    return data  # type: ignore[return-value]


@router.post("/compare-batches", response_model=CompareBatchesResponse)
async def compare(
    body: CompareBatchesRequest,
    db: AsyncSession = Depends(get_db),
) -> CompareBatchesResponse:
    data = await compare_batches(db, body.batch_ids)
    return data  # type: ignore[return-value]


