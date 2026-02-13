from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BatchCreateItem(BaseModel):
    СтатусЗакрытия: bool = Field(default=False)
    ПредставлениеЗаданияНаСмену: str
    РабочийЦентр: str
    Смена: str
    Бригада: str
    НомерПартии: int
    ДатаПартии: date
    Номенклатура: str
    КодЕКН: str
    ИдентификаторРЦ: str
    ДатаВремяНачалаСмены: datetime
    ДатаВремяОкончанияСмены: datetime


class ProductInBatch(BaseModel):
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchRead(BaseModel):
    id: int
    is_closed: bool
    batch_number: int
    batch_date: date
    products: List[ProductInBatch] = []

    class Config:
        from_attributes = True


class BatchUpdate(BaseModel):
    is_closed: Optional[bool] = None
    task_description: Optional[str] = None
    shift: Optional[str] = None
    team: Optional[str] = None



