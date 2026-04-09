"""
Redis-backed (with fakeredis fallback) cache manager for Football Predictor.

Cache keys follow the pattern:
    api:{provider}:{path}:{params_hash}

TTL is configurable via the API_CACHE_TTL_SECONDS env var (default 300s).
If Redis is unavailable, falls back to an in-memory dict silently.
"""

import hashlib
import json
import time
from typing import Any, Optional

from config import REDIS_URL, API_CACHE_TTL_SECONDS
from logger import get_logger

logger = get_logger(__name__)


def _make_key(provider: str, path: str, params: Optional[dict] = None) -> str:
    """Build a deterministic cache key."""
    params_str = json.dumps(params or {}, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
    return f"api:{provider}:{path}:{params_hash}"


# ── In-memory fallback ────────────────────────────────────────────────────────

class _MemoryCache:
    """Simple TTL-aware dict for local development fallback."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry["expires"]:
            del self._store[key]
            return None
        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = API_CACHE_TTL_SECONDS) -> None:
        self._store[key] = {
            "value": value,
            "expires": time.monotonic() + ttl,
        }

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


# ── CacheManager ──────────────────────────────────────────────────────────────

class CacheManager:
    """
    Unified cache interface.

    Tries to connect to Redis on construction; falls back to in-memory
    dict if Redis is unavailable or REDIS_URL is not set.
    """

    def __init__(self):
        self._redis = None
        self._fallback = _MemoryCache()
        self._default_ttl = API_CACHE_TTL_SECONDS
        self._using_redis = False

        if REDIS_URL:
            self._try_connect_redis()
        else:
            self._try_fakeredis()

    def _try_connect_redis(self) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore
            self._redis = aioredis.from_url(REDIS_URL, decode_responses=False)
            self._using_redis = True
            logger.info("CacheManager: connected to Redis at %s", REDIS_URL)
        except Exception as exc:
            logger.warning(
                "CacheManager: Redis connection failed (%s), using in-memory fallback", exc
            )

    def _try_fakeredis(self) -> None:
        try:
            import fakeredis  # type: ignore
            self._redis = fakeredis.FakeRedis(decode_responses=False)
            self._using_redis = True
            logger.info("CacheManager: using fakeredis (local dev mode)")
        except ImportError:
            logger.info("CacheManager: fakeredis not installed, using in-memory dict")

    # ── Public API ────────────────────────────────────────────────────────────

    def build_key(self, provider: str, path: str, params: Optional[dict] = None) -> str:
        return _make_key(provider, path, params)

    async def get(self, key: str) -> Optional[Any]:
        if self._using_redis and self._redis is not None:
            try:
                raw = self._redis.get(key)
                if hasattr(raw, "__await__"):  # async redis
                    raw = await raw
                if raw is None:
                    logger.debug("Cache MISS: %s", key)
                    return None
                logger.debug("Cache HIT: %s", key)
                return json.loads(raw)
            except Exception as exc:
                logger.warning("Cache get error (%s), falling back", exc)
        # In-memory fallback
        value = self._fallback.get(key)
        if value is None:
            logger.debug("Cache MISS (mem): %s", key)
        else:
            logger.debug("Cache HIT (mem): %s", key)
        return value

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        ttl = ttl or self._default_ttl
        if self._using_redis and self._redis is not None:
            try:
                encoded = json.dumps(value, default=str).encode()
                result = self._redis.setex(key, ttl, encoded)
                if hasattr(result, "__await__"):
                    await result
                return
            except Exception as exc:
                logger.warning("Cache set error (%s), falling back", exc)
        self._fallback.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        if self._using_redis and self._redis is not None:
            try:
                result = self._redis.delete(key)
                if hasattr(result, "__await__"):
                    await result
                return
            except Exception as exc:
                logger.warning("Cache delete error (%s)", exc)
        self._fallback.delete(key)

    async def clear(self) -> None:
        if self._using_redis and self._redis is not None:
            try:
                result = self._redis.flushdb()
                if hasattr(result, "__await__"):
                    await result
                return
            except Exception as exc:
                logger.warning("Cache flush error (%s)", exc)
        self._fallback.clear()

    def info(self) -> dict:
        return {
            "backend": "redis" if (self._using_redis and REDIS_URL) else (
                "fakeredis" if self._using_redis else "memory"
            ),
            "ttl_seconds": self._default_ttl,
        }


# Singleton
cache_manager = CacheManager()
