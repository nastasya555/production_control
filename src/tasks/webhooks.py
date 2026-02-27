from __future__ import annotations

import json
import logging
from datetime import datetime

import httpx
from celery import shared_task
from sqlalchemy.orm import Session

from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.tasks.base import DatabaseTask
from src.utils.hmac_utils import sign_payload


logger = logging.getLogger(__name__)


@shared_task(bind=True, base=DatabaseTask, max_retries=3)
def send_webhook_delivery(self, delivery_id: int) -> None:
    session: Session = self.get_session()  # type: ignore[attr-defined]

    try:
        delivery = session.get(WebhookDelivery, delivery_id)
        if delivery is None:
            return

        subscription = session.get(WebhookSubscription, delivery.subscription_id)
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

        with httpx.Client(timeout=timeout) as client:
            try:
                resp = client.post(subscription.url, content=body_bytes, headers=headers)
                delivery.attempts += 1
                delivery.response_status = resp.status_code
                delivery.response_body = resp.text
                if 200 <= resp.status_code < 300:
                    delivery.status = "success"
                    delivery.delivered_at = datetime.utcnow()
                else:
                    delivery.status = "failed"
                    delivery.error_message = f"HTTP {resp.status_code}"
            except httpx.HTTPError as exc:
                delivery.attempts += 1
                delivery.status = "failed"
                delivery.error_message = str(exc)
                logger.error(
                    "HTTP error when sending webhook",
                    exc_info=True,
                    extra={"delivery_id": delivery_id},
                )
            except Exception as exc:
                delivery.attempts += 1
                delivery.status = "failed"
                delivery.error_message = str(exc)
                logger.critical(
                    "Unexpected error in send_webhook_delivery",
                    exc_info=True,
                    extra={"delivery_id": delivery_id},
                )
                raise

            session.commit()

            if (
                delivery.status != "success"
                and delivery.attempts < subscription.retry_count
            ):
                raise self.retry(
                    exc=Exception("Webhook failed, retry"),
                    countdown=2 ** delivery.attempts,
                )
    finally:
        session.close()