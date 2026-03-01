from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BatchReportRequest(BaseModel):
    format: str = Field(default="excel", pattern="^(excel|pdf)$")
    email: Optional[str] = None


class BatchExportRequest(BaseModel):
    format: str = Field(default="excel", pattern="^(excel|csv)$")
    filters: Dict[str, Any]


