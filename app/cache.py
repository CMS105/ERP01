import json
import logging
from typing import Any, Optional
from datetime import datetime, timezone
import redis
from app.config import settings

logger = logging.getLogger("app.cache")

class CacheService:
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._is_redis_available = False
        self._init_client()

    def _init_client(self):
        try:
            client = redis.from_url(
                settings.REDIS_URL,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                decode_responses=True
            )
            client.ping()
            self._redis_client = client
            self._is_redis_available = True
        except Exception:
            self._redis_client = None
            self._is_redis_available = False

    def is_available(self) -> bool:
        if self._is_redis_available and self._redis_client:
            try:
                self._redis_client.ping()
                return True
            except Exception:
                self._is_redis_available = False
                return False
        return False

    def get(self, key: str) -> Optional[Any]:
        if self.is_available() and self._redis_client:
            try:
                val = self._redis_client.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass

        if key in self._memory_cache:
            data, exp = self._memory_cache[key]
            if datetime.now(timezone.utc).timestamp() < exp:
                return data
            else:
                del self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        ttl = ttl_seconds or settings.CACHE_DEFAULT_TTL_SECONDS
        serialized = json.dumps(value, default=str)

        if self.is_available() and self._redis_client:
            try:
                self._redis_client.setex(key, ttl, serialized)
                return True
            except Exception:
                pass

        exp = datetime.now(timezone.utc).timestamp() + ttl
        self._memory_cache[key] = (value, exp)
        return True

    def delete(self, key: str) -> bool:
        if self.is_available() and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        self._memory_cache.pop(key, None)
        return True

    def delete_pattern(self, pattern: str) -> int:
        count = 0
        if self.is_available() and self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    count = self._redis_client.delete(*keys)
            except Exception:
                pass

        prefix = pattern.replace("*", "")
        to_del = [k for k in self._memory_cache if prefix in k]
        for k in to_del:
            self._memory_cache.pop(k, None)
            count += 1
        return count

    def clear(self):
        if self.is_available() and self._redis_client:
            try:
                self._redis_client.flushdb()
            except Exception:
                pass
        self._memory_cache.clear()

cache = CacheService()
