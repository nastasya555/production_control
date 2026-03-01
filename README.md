## Система контроля заданий на выпуск продукции

Бэкенд‑сервис на FastAPI с использованием PostgreSQL, Redis, RabbitMQ, Celery и MinIO
для управления сменными заданиями (партиями), продукцией и интеграциями (webhooks, отчёты).

### Локальный запуск (через Docker Compose)

1. Скопировать файл `.env.example` в `.env` и заполнить реальные значения (пароли, URL и т.д.).
2. Собрать и запустить контейнеры:

```bash
docker compose up --build
```

3. После старта:
   - API: `http://localhost:8000` (Swagger по адресу `/docs`)
   - Flower: `http://localhost:5555`
   - MinIO: `http://localhost:9000` (консоль `http://localhost:9001`)

### Стек

- Python 3.11
- FastAPI, SQLAlchemy (async), Pydantic v2
- PostgreSQL, Alembic
- Celery, RabbitMQ, Redis
- MinIO (S3‑совместимое хранилище)

Детали API, моделей и задач Celery описаны в техническом задании.



