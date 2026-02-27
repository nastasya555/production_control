from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import delete_pattern, get_redis
from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.product_repository import ProductRepository
from src.data.repositories.work_center_repository import WorkCenterRepository
from src.data.repositories.webhook_repository import (
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)


class UnitOfWork:
    """
    Unit of Work для управления транзакциями и инвалидацией кэша.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.batches = BatchRepository(session)
        self.products = ProductRepository(session)
        self.work_centers = WorkCenterRepository(session)
        self.webhook_subscriptions = WebhookSubscriptionRepository(session)
        self.webhook_deliveries = WebhookDeliveryRepository(session)
        self._committed = False

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            # если забыли вызвать commit — не оставляем грязную транзакцию
            await self.rollback()

    async def commit(self) -> None:
        await self.session.commit()
        self._committed = True
        await self._invalidate_cache()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def _invalidate_cache(self) -> None:
        redis = get_redis()
        await redis.delete("dashboard_stats")
        await delete_pattern("batch_statistics*")
        await delete_pattern("compare_batches*")

