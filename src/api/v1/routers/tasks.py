from __future__ import annotations

from fastapi import APIRouter
from celery.result import AsyncResult

from src.api.v1.schemas.tasks import TaskStatusResponse
from src.celery_app import celery_app


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    value = result.result
    if isinstance(value, Exception):
        value = {
            "error": value.__class__.__name__,
            "message": str(value),
        }
    return TaskStatusResponse(task_id=task_id, status=result.status, result=value)



