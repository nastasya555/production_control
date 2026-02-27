from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.webhook_service import WebhookService
from src.tasks.webhooks import send_webhook_delivery


class EventDispatcher:
    """
    Простой диспетчер доменных событий: создаёт delivery и ставит Celery-задачи на отправку.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.webhook_service = WebhookService(session)

    async def dispatch(self, event_type: str, payload: dict) -> None:
        deliveries = await self.webhook_service.create_deliveries_for_event(event_type, payload)
        for delivery in deliveries:
            send_webhook_delivery.delay(delivery.id)

