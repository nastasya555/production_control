from __future__ import annotations

# Импорты модулей с задачами, чтобы Celery их зарегистрировал при старте воркера
from src.tasks import aggregation as _aggregation  # noqa: F401
from src.tasks import reports as _reports  # noqa: F401
from src.tasks import imports as _imports  # noqa: F401
from src.tasks import exports as _exports  # noqa: F401
from src.tasks import webhooks as _webhooks  # noqa: F401
from src.tasks import scheduled as _scheduled  # noqa: F401


