from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class BatchCreateItem(BaseModel):
    """
    Входная схема создания партии.

    Принимает как русские поля из 1С, так и английские:
    - СтатусЗакрытия ↔ is_closed
    - ПредставлениеЗаданияНаСмену ↔ task_description
    - РабочийЦентр ↔ work_center_name
    - Смена ↔ shift
    - Бригада ↔ team
    - НомерПартии ↔ batch_number
    - ДатаПартии ↔ batch_date
    - Номенклатура ↔ nomenclature
    - КодЕКН ↔ ekn_code
    - ИдентификаторРЦ ↔ work_center_identifier
    - ДатаВремяНачалаСмены ↔ shift_start
    - ДатаВремяОкончанияСмены ↔ shift_end
    """

    model_config = ConfigDict(populate_by_name=True)

    is_closed: bool = Field(default=False, alias="СтатусЗакрытия")
    task_description: str = Field(alias="ПредставлениеЗаданияНаСмену")
    work_center_name: str = Field(alias="РабочийЦентр")
    shift: str = Field(alias="Смена")
    team: str = Field(alias="Бригада")
    batch_number: int = Field(alias="НомерПартии")
    batch_date: date = Field(alias="ДатаПартии")
    nomenclature: str = Field(alias="Номенклатура")
    ekn_code: str = Field(alias="КодЕКН")
    work_center_identifier: str = Field(alias="ИдентификаторРЦ")
    shift_start: datetime = Field(alias="ДатаВремяНачалаСмены")
    shift_end: datetime = Field(alias="ДатаВремяОкончанияСмены")


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



