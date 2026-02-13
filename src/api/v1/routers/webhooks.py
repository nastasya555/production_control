from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.webhook import (
    WebhookDeliveryRead,
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
    WebhookSubscriptionUpdate,
)
from src.core.database import get_db
from src.data.models.webhook import WebhookSubscription
from src.domain.services.webhook_service import WebhookService


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookSubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: WebhookSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionRead:
    service = WebhookService(db)
    sub = await service.create_subscription(payload.model_dump())
    return sub


@router.get("", response_model=List[WebhookSubscriptionRead])
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
) -> List[WebhookSubscriptionRead]:
    service = WebhookService(db)
    subs = await service.list_subscriptions()
    return list(subs)


@router.patch("/{webhook_id}", response_model=WebhookSubscriptionRead)
async def update_subscription(
    webhook_id: int,
    payload: WebhookSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionRead:
    sub = await db.get(WebhookSubscription, webhook_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")
    service = WebhookService(db)
    updated = await service.update_subscription(sub, payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/{webhook_id}", status_code=status.HTTP_200_OK)
async def delete_subscription(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = await db.get(WebhookSubscription, webhook_id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )
    await db.delete(sub)
    await db.commit()
    return {"status": "deleted"}


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryRead])
async def list_deliveries(
    webhook_id: int,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[WebhookDeliveryRead]:
    service = WebhookService(db)
    deliveries = await service.list_deliveries(webhook_id, offset=offset, limit=limit)
    return list(deliveries)


