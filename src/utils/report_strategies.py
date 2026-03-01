from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from src.data.models.batch import Batch
from src.data.models.product import Product
from src.utils.excel_generator import generate_batch_report_excel, generate_batch_report_pdf


class ReportStrategy(ABC):
    @property
    @abstractmethod
    def file_extension(self) -> str:  # например ".xlsx"
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        batch: Batch,
        products: Iterable[Product],
        file_path: str,
    ) -> None:
        raise NotImplementedError


class ExcelReportStrategy(ReportStrategy):
    @property
    def file_extension(self) -> str:
        return ".xlsx"

    def generate(
        self,
        batch: Batch,
        products: Iterable[Product],
        file_path: str,
    ) -> None:
        generate_batch_report_excel(batch, products, file_path)


class PdfReportStrategy(ReportStrategy):
    @property
    def file_extension(self) -> str:
        return ".pdf"

    def generate(self, batch: Batch, products: Iterable[Product], file_path: str) -> None:
        generate_batch_report_pdf(batch, products, file_path)


class ReportFactory:
    _strategies: dict[str, ReportStrategy] = {
        "excel": ExcelReportStrategy(),
        "pdf": PdfReportStrategy(),
    }

    @classmethod
    def get_strategy(cls, format: str) -> ReportStrategy:
        fmt = (format or "excel").lower()
        strategy = cls._strategies.get(fmt)
        if strategy is None:
            raise ValueError(f"Unsupported report format: {format}")
        return strategy

