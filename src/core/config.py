from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_title: str = Field(default="Production Control API", alias="APP_TITLE")

    # Async URL для FastAPI
    database_url_async: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/production_control",
        alias="DATABASE_URL_ASYNC",
    )
    # Sync URL для Celery задач
    database_url_sync: str = Field(
        default="postgresql://postgres:postgres@postgres:5432/production_control",
        alias="DATABASE_URL_SYNC",
    )

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="amqp://admin:admin@rabbitmq:5672//", alias="CELERY_BROKER_URL"
    )

    celery_result_backend: str = Field(
        default="redis://redis:6379/1", alias="CELERY_RESULT_BACKEND"
    )

    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: SecretStr = Field(
        default=SecretStr("minioadmin"), alias="MINIO_ACCESS_KEY"
    )
    minio_secret_key: SecretStr = Field(
        default=SecretStr("minioadmin"), alias="MINIO_SECRET_KEY"
    )
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-jwt-secret"), alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expires_minutes: int = Field(
        default=60, alias="JWT_ACCESS_TOKEN_EXPIRES_MINUTES"
    )

    max_upload_mb: int = Field(default=100, alias="MAX_UPLOAD_MB")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @field_validator("minio_access_key", "minio_secret_key")
    @classmethod
    def _validate_minio_creds(cls, v: SecretStr, info):
        # В проде запрещаем дефолтные креды
        env = info.data.get("app_env", "dev")
        if env != "dev" and v.get_secret_value() == "minioadmin":
            raise ValueError("MINIO credentials must be overridden in production")
        return v

    @field_validator("celery_broker_url")
    @classmethod
    def _validate_broker(cls, v: str, info):
        env = info.data.get("app_env", "dev")
        if env != "dev" and "admin:admin@" in v:
            raise ValueError("CELERY_BROKER_URL must use non-default credentials in production")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
