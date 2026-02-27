from fastapi import FastAPI

from src.core.config import settings
from src.api.v1.routers import batches, products, tasks, webhooks, analytics
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        debug=settings.app_debug,
    )

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "ok"}

    app.include_router(batches.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")

    return app


app = create_app()


