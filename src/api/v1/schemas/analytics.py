from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_batches: int
    active_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float


class DashboardToday(BaseModel):
    batches_created: int
    batches_closed: int
    products_added: int
    products_aggregated: int


class DashboardShiftStats(BaseModel):
    batches: int
    products: int
    aggregated: int


class DashboardTopWorkCenter(BaseModel):
    id: str
    name: str
    batches_count: int
    products_count: int
    aggregation_rate: float


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    today: DashboardToday
    by_shift: dict[str, DashboardShiftStats]
    top_work_centers: List[DashboardTopWorkCenter]
    cached_at: datetime


class BatchInfo(BaseModel):
    id: int
    batch_number: int
    batch_date: date
    is_closed: bool


class ProductionStats(BaseModel):
    total_products: int
    aggregated: int
    remaining: int
    aggregation_rate: float


class TimelineStats(BaseModel):
    shift_duration_hours: float
    elapsed_hours: float
    products_per_hour: float
    estimated_completion: Optional[datetime] = None


class TeamPerformance(BaseModel):
    team: str
    avg_products_per_hour: float
    efficiency_score: float


class BatchStatisticsResponse(BaseModel):
    batch_info: BatchInfo
    production_stats: ProductionStats
    timeline: TimelineStats
    team_performance: TeamPerformance


class CompareBatchesRequest(BaseModel):
    batch_ids: List[int]


class CompareBatchItem(BaseModel):
    batch_id: int
    batch_number: int
    total_products: int
    aggregated: int
    rate: float
    duration_hours: float
    products_per_hour: float


class CompareBatchesAverage(BaseModel):
    aggregation_rate: float
    products_per_hour: float


class CompareBatchesResponse(BaseModel):
    comparison: List[CompareBatchItem]
    average: CompareBatchesAverage


