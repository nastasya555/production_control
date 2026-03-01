from __future__ import annotations

from celery import Task
from sqlalchemy.orm import Session

from src.core.database import SyncSessionLocal


class DatabaseTask(Task):
    """
    Базовый класс Celery-задач с доступом к синхронной БД-сессии.
    """

    def get_session(self) -> Session:
        return SyncSessionLocal()

