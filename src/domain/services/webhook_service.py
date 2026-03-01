from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.data.repositories.webhook_repository import (
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sub_repo = WebhookSubscriptionRepository(session)
        self.deliv_repo = WebhookDeliveryRepository(session)

    async def create_subscription(self, data: dict) -> WebhookSubscription:
        sub = await self.sub_repo.create(data)
        await self.session.commit()
        return sub

    async def update_subscription(self, sub: WebhookSubscription, data: dict) -> WebhookSubscription:
        sub = await self.sub_repo.update(sub, data)
        await self.session.commit()
        return sub

    async def list_subscriptions(self) -> Iterable[WebhookSubscription]:
        return await self.sub_repo.list()

    async def list_deliveries(self, subscription_id: int, offset: int = 0, limit: int = 50) -> Iterable[WebhookDelivery]:
        return await self.deliv_repo.list_for_subscription(subscription_id, offset=offset, limit=limit)

    async def create_deliveries_for_event(self, event_type: str, payload: dict) -> Sequence[WebhookDelivery]:
        """
        Создаёт записи WebhookDelivery для всех активных подписок и возвращает их.
        """
        subs = await self.sub_repo.get_active_for_event(event_type)
        deliveries: list[WebhookDelivery] = []
        for sub in subs:
            delivery = await self.deliv_repo.create(
                {
                    "subscription_id": sub.id,
                    "event_type": event_type,
                    "payload": payload,
                    "status": "pending",
                }
            )
            deliveries.append(delivery)
        await self.session.commit()
        return deliveries


