from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field


class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl
    events: List[str]
    secret_key: str
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=10, ge=1, le=60)


class WebhookSubscriptionUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    secret_key: Optional[str] = None
    retry_count: Optional[int] = Field(default=None, ge=0, le=10)
    timeout: Optional[int] = Field(default=None, ge=1, le=60)
    is_active: Optional[bool] = None


class WebhookSubscriptionRead(BaseModel):
    id: int
    url: HttpUrl
    events: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryRead(BaseModel):
    id: int
    event_type: str
    status: str
    attempts: int
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


