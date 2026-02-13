from __future__ import annotations

import json
from datetime import datetime

import httpx
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.utils.hmac_utils import sign_payload


engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@shared_task(bind=True, max_retries=3)
def send_webhook_delivery(self, delivery_id: int) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            delivery = await session.get(WebhookDelivery, delivery_id)
            if delivery is None:
                return

            subscription = await session.get(WebhookSubscription, delivery.subscription_id)
            if subscription is None or not subscription.is_active:
                return

            body_bytes = json.dumps(
                {
                    "event": delivery.event_type,
                    "data": delivery.payload,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                default=str,
            ).encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "X-Event-Type": delivery.event_type,
                "X-Delivery-Id": str(delivery.id),
                "X-Signature": sign_payload(subscription.secret_key, body_bytes),
            }

            timeout = subscription.timeout

            async with httpx.AsyncClient(timeout=timeout) as client:
                try:
                    resp = await client.post(subscription.url, content=body_bytes, headers=headers)
                    delivery.attempts += 1
                    delivery.response_status = resp.status_code
                    delivery.response_body = resp.text
                    if 200 <= resp.status_code < 300:
                        delivery.status = "success"
                        delivery.delivered_at = datetime.utcnow()
                    else:
                        delivery.status = "failed"
                        delivery.error_message = f"HTTP {resp.status_code}"
                except Exception as exc:  # noqa: BLE001
                    delivery.attempts += 1
                    delivery.status = "failed"
                    delivery.error_message = str(exc)

                await session.commit()

                # планируем ретрай, если ещё можно
                if (
                    delivery.status != "success"
                    and delivery.attempts < subscription.retry_count
                ):
                    raise self.retry(exc=Exception("Webhook failed, retry"), countdown=2**delivery.attempts)

    import asyncio

    return asyncio.run(_run())


