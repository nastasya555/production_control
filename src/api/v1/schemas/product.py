from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProductCreate(BaseModel):
    batch_id: int
    unique_code: str


class ProductRead(BaseModel):
    id: int
    unique_code: str
    batch_id: int
    is_aggregated: bool
    aggregated_at: Optional[datetime] = None

    class Config:
        from_attributes = True



