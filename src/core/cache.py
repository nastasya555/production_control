from typing import Any, Awaitable, Callable, TypeVar

import asyncio
import functools
import hashlib
import json

from redis.asyncio import Redis

from src.core.config import settings


_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _make_cache_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def cached(ttl: int, key_prefix: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            redis = get_redis()
            key = _make_cache_key(key_prefix, args, kwargs)
            cached_value = await redis.get(key)
            if cached_value is not None:
                return json.loads(cached_value)

            result = await func(*args, **kwargs)
            await redis.set(key, json.dumps(result, default=str), ex=ttl)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


async def delete_pattern(pattern: str) -> None:
    redis = get_redis()
    cursor = 0
    keys: list[str] = []
    while True:
        cursor, batch = await redis.scan(cursor=cursor, match=pattern, count=100)
        keys.extend(batch)
        if cursor == 0:
            break
    if keys:
        await redis.delete(*keys)



