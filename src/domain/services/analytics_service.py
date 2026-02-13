from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import cached
from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.work_center import WorkCenter


@cached(ttl=300, key_prefix="dashboard_stats")
async def get_dashboard_statistics(db: AsyncSession) -> dict:
    total_batches = await db.scalar(select(func.count(Batch.id))) or 0
    closed_batches = await db.scalar(select(func.count()).where(Batch.is_closed.is_(True))) or 0
    active_batches = total_batches - closed_batches

    total_products = await db.scalar(select(func.count(Product.id))) or 0
    aggregated_products = (
        await db.scalar(select(func.count()).where(Product.is_aggregated.is_(True))) or 0
    )
    aggregation_rate = (aggregated_products / total_products * 100) if total_products else 0.0

    today = datetime.now().date()
    batches_created = (
        await db.scalar(select(func.count()).where(func.date(Batch.created_at) == today)) or 0
    )
    batches_closed = (
        await db.scalar(
            select(func.count()).where(
                Batch.is_closed.is_(True),
                func.date(Batch.closed_at) == today,
            )
        )
        or 0
    )
    products_added = (
        await db.scalar(select(func.count()).where(func.date(Product.created_at) == today)) or 0
    )
    products_aggregated = (
        await db.scalar(
            select(func.count()).where(
                Product.is_aggregated.is_(True),
                func.date(Product.aggregated_at) == today,
            )
        )
        or 0
    )

    by_shift_rows = (
        await db.execute(
            select(
                Batch.shift,
                func.count(Batch.id),
                func.count(Product.id),
                func.sum(func.cast(Product.is_aggregated, func.INTEGER())),
            )
            .join(Product, Product.batch_id == Batch.id, isouter=True)
            .group_by(Batch.shift)
        )
    ).all()

    by_shift: dict[str, dict] = {}
    for shift, b_count, p_count, agg_count in by_shift_rows:
        p_count = p_count or 0
        agg_count = agg_count or 0
        by_shift[shift] = {
            "batches": b_count or 0,
            "products": p_count,
            "aggregated": agg_count,
        }

    top_wc_rows = (
        await db.execute(
            select(
                WorkCenter.identifier,
                WorkCenter.name,
                func.count(Batch.id),
                func.count(Product.id),
                func.coalesce(func.avg(func.cast(Product.is_aggregated, func.FLOAT())) * 100, 0),
            )
            .join(Batch, Batch.work_center_id == WorkCenter.id)
            .join(Product, Product.batch_id == Batch.id, isouter=True)
            .group_by(WorkCenter.id)
            .order_by(func.count(Batch.id).desc())
            .limit(10)
        )
    ).all()

    top_work_centers: List[dict] = []
    for ident, name, b_count, p_count, rate in top_wc_rows:
        top_work_centers.append(
            {
                "id": ident,
                "name": name,
                "batches_count": b_count or 0,
                "products_count": p_count or 0,
                "aggregation_rate": float(rate or 0),
            }
        )

    return {
        "summary": {
            "total_batches": total_batches,
            "active_batches": active_batches,
            "closed_batches": closed_batches,
            "total_products": total_products,
            "aggregated_products": aggregated_products,
            "aggregation_rate": round(aggregation_rate, 2),
        },
        "today": {
            "batches_created": batches_created,
            "batches_closed": batches_closed,
            "products_added": products_added,
            "products_aggregated": products_aggregated,
        },
        "by_shift": by_shift,
        "top_work_centers": top_work_centers,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }


@cached(ttl=300, key_prefix="batch_statistics")
async def get_batch_statistics(db: AsyncSession, batch_id: int) -> dict:
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise ValueError("Batch not found")

    totals = (
        await db.execute(
            select(
                func.count(Product.id),
                func.count().filter(Product.is_aggregated.is_(True)),
            ).where(Product.batch_id == batch_id)
        )
    ).one()
    total_products = totals[0] or 0
    aggregated = totals[1] or 0
    remaining = total_products - aggregated
    rate = (aggregated / total_products * 100) if total_products else 0.0

    shift_duration_hours = (batch.shift_end - batch.shift_start).total_seconds() / 3600
    now = datetime.now(timezone.utc)
    elapsed_hours = max((min(now, batch.shift_end) - batch.shift_start).total_seconds() / 3600, 0)
    products_per_hour = (aggregated / elapsed_hours) if elapsed_hours > 0 else 0.0
    estimated_completion = None
    if products_per_hour > 0 and remaining > 0:
        remaining_hours = remaining / products_per_hour
        estimated_completion = (now + timedelta(hours=remaining_hours)).isoformat()

    efficiency_score = min(100.0, products_per_hour * 1.0)

    return {
        "batch_info": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "batch_date": batch.batch_date,
            "is_closed": batch.is_closed,
        },
        "production_stats": {
            "total_products": total_products,
            "aggregated": aggregated,
            "remaining": remaining,
            "aggregation_rate": round(rate, 2),
        },
        "timeline": {
            "shift_duration_hours": round(shift_duration_hours, 2),
            "elapsed_hours": round(elapsed_hours, 2),
            "products_per_hour": round(products_per_hour, 2),
            "estimated_completion": estimated_completion,
        },
        "team_performance": {
            "team": batch.team,
            "avg_products_per_hour": round(products_per_hour, 2),
            "efficiency_score": round(efficiency_score, 2),
        },
    }


@cached(ttl=300, key_prefix="compare_batches")
async def compare_batches(db: AsyncSession, batch_ids: list[int]) -> dict:
    rows = (
        await db.execute(
            select(
                Batch.id,
                Batch.batch_number,
                Batch.shift_start,
                Batch.shift_end,
                func.count(Product.id),
                func.count().filter(Product.is_aggregated.is_(True)),
            )
            .join(Product, Product.batch_id == Batch.id, isouter=True)
            .where(Batch.id.in_(batch_ids))
            .group_by(Batch.id)
        )
    ).all()

    comparison: list[dict] = []
    total_rate = 0.0
    total_pph = 0.0

    for bid, num, start, end, total_p, agg_p in rows:
        total_p = total_p or 0
        agg_p = agg_p or 0
        rate = (agg_p / total_p * 100) if total_p else 0.0
        duration_hours = (end - start).total_seconds() / 3600
        pph = (agg_p / duration_hours) if duration_hours > 0 else 0.0

        comparison.append(
            {
                "batch_id": bid,
                "batch_number": num,
                "total_products": total_p,
                "aggregated": agg_p,
                "rate": round(rate, 2),
                "duration_hours": round(duration_hours, 2),
                "products_per_hour": round(pph, 2),
            }
        )
        total_rate += rate
        total_pph += pph

    n = len(comparison) or 1
    avg_rate = total_rate / n
    avg_pph = total_pph / n

    return {
        "comparison": comparison,
        "average": {
            "aggregation_rate": round(avg_rate, 2),
            "products_per_hour": round(avg_pph, 2),
        },
    }


