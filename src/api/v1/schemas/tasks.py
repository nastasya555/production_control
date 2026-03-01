from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None



