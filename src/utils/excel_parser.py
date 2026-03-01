from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def parse_batches_file(path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Читает Excel/CSV с партиями и возвращает:
    - список словарей с полями для BatchService.create_batches
    - список ошибок формата {"row": int, "error": str}
    """
    file_path = Path(path)

    if file_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    df = df.fillna("")

    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, row in df.iterrows():
        try:
            data = {
                "НомерПартии": int(row["НомерПартии"]),
                "ДатаПартии": pd.to_datetime(row["ДатаПартии"]).date(),
                "Номенклатура": str(row["Номенклатура"]),
                "РабочийЦентр": str(row.get("РабочийЦентр", "")),
                "Смена": str(row.get("Смена", "")),
                "Бригада": str(row.get("Бригада", "")),
                "КодЕКН": str(row.get("КодЕКН", "")),
                "ИдентификаторРЦ": str(row.get("ИдентификаторРЦ", "")),
                "ПредставлениеЗаданияНаСмену": str(row.get("ПредставлениеЗаданияНаСмену", "")),
                "СтатусЗакрытия": bool(row.get("СтатусЗакрытия", False)),
                "ДатаПартииСтрока": str(row["ДатаПартии"]),
            }

            # Временные поля можно задать по умолчанию, если нет в файле
            now = datetime.now()
            data["ДатаВремяНачалаСмены"] = pd.to_datetime(
                row.get("ДатаВремяНачалаСмены", now)
            ).to_pydatetime()
            data["ДатаВремяОкончанияСмены"] = pd.to_datetime(
                row.get("ДатаВремяОкончанияСмены", now)
            ).to_pydatetime()

            items.append(data)
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": int(idx) + 2, "error": str(exc)})

    return items, errors


