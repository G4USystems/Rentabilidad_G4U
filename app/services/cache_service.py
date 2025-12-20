"""Redis caching service for KPIs and expensive queries."""

import json
import logging
import os
from datetime import timedelta
from typing import Any, Optional, Callable, TypeVar
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheService:
    """
    Redis-based caching service.

    Falls back to in-memory cache if Redis is not available.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis_client = None
        self._memory_cache: dict = {}
        self._initialized = False

    async def _get_redis(self):
        """Lazy initialization of Redis client."""
        if self._initialized:
            return self._redis_client

        self._initialized = True

        if not self.redis_url:
            logger.info("No REDIS_URL configured, using in-memory cache")
            return None

        try:
            import redis.asyncio as redis
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis_client.ping()
            logger.info("Redis cache connected")
            return self._redis_client
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using in-memory cache")
            self._redis_client = None
            return None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        redis = await self._get_redis()

        if redis:
            try:
                value = await redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                return None
        else:
            return self._memory_cache.get(key)

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,
    ) -> bool:
        """Set value in cache with TTL."""
        redis = await self._get_redis()

        try:
            serialized = json.dumps(value, default=str)

            if redis:
                await redis.setex(key, ttl_seconds, serialized)
            else:
                # In-memory fallback (no TTL support for simplicity)
                self._memory_cache[key] = json.loads(serialized)

            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        redis = await self._get_redis()

        try:
            if redis:
                await redis.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        redis = await self._get_redis()

        if redis:
            try:
                keys = []
                async for key in redis.scan_iter(pattern):
                    keys.append(key)
                if keys:
                    await redis.delete(*keys)
                return len(keys)
            except Exception as e:
                logger.error(f"Cache clear pattern error: {e}")
                return 0
        else:
            # In-memory: simple prefix match
            to_delete = [k for k in self._memory_cache.keys() if k.startswith(pattern.replace("*", ""))]
            for k in to_delete:
                del self._memory_cache[k]
            return len(to_delete)

    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl_seconds: int = 300,
    ) -> Any:
        """Get from cache or compute and store."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        # Compute value
        if callable(factory):
            value = await factory() if hasattr(factory, '__await__') else factory()
        else:
            value = factory

        await self.set(key, value, ttl_seconds)
        return value


# Singleton instance
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(prefix: str, ttl_seconds: int = 300):
    """
    Decorator for caching async function results.

    Usage:
        @cached("kpi:dashboard", ttl_seconds=60)
        async def get_dashboard_kpis(start_date, end_date):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            key = f"{prefix}:{cache_key(*args[1:], **kwargs)}"  # Skip self

            cached_value = await cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value

            logger.debug(f"Cache miss: {key}")
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


class CachedKPIService:
    """Wrapper for FinancialService with caching."""

    def __init__(self, financial_service, cache: Optional[CacheService] = None):
        self.financial = financial_service
        self.cache = cache or get_cache()
        self.default_ttl = 300  # 5 minutes

    async def get_total_revenue(self, start_date, end_date) -> float:
        """Get total revenue with caching."""
        key = f"kpi:revenue:{start_date}:{end_date}"
        return await self.cache.get_or_set(
            key,
            lambda: self.financial.get_total_revenue(start_date, end_date),
            self.default_ttl,
        )

    async def get_total_expenses(self, start_date, end_date) -> float:
        """Get total expenses with caching."""
        key = f"kpi:expenses:{start_date}:{end_date}"
        return await self.cache.get_or_set(
            key,
            lambda: self.financial.get_total_expenses(start_date, end_date),
            self.default_ttl,
        )

    async def invalidate_kpis(self):
        """Invalidate all KPI caches."""
        await self.cache.clear_pattern("kpi:*")
        logger.info("KPI cache invalidated")
