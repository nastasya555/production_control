from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import settings


class Base(DeclarativeBase):
    pass


# Async engine / session для FastAPI
engine: AsyncEngine = create_async_engine(
    settings.database_url_async,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# Sync engine / session для Celery задач
sync_engine = create_engine(
    settings.database_url_sync,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, class_=Session)




