import json
import logging
import redis.asyncio as redis
from typing import Any, Optional, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheClient:
    """
    Redis implementation for aggressive caching of external API responses
    to protect free-tier limits.
    """
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        # Default TTL is 24 hours
        self.default_ttl = 86400 

    async def get_cached_response(self, source: str, query_key: str) -> Optional[Any]:
        """Retrieves a cached JSON response if it exists."""
        key = f"cache:{source}:{query_key}"
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug(f"Cache HIT for {key}")
                return json.loads(data)
            logger.debug(f"Cache MISS for {key}")
            return None
        except Exception as e:
            logger.error(f"Redis GET error for {key}: {str(e)}")
            return None

    async def set_cached_response(self, source: str, query_key: str, data: Any, ttl: int = None) -> bool:
        """Caches a JSON response with a TTL."""
        key = f"cache:{source}:{query_key}"
        expiry = ttl if ttl is not None else self.default_ttl
        try:
            await self.redis.setex(key, expiry, json.dumps(data))
            logger.debug(f"Cached data for {key} (TTL: {expiry}s)")
            return True
        except Exception as e:
            logger.error(f"Redis SET error for {key}: {str(e)}")
            return False
            
    async def clear_cache(self, pattern: str = "cache:*"):
        """Utility to clear cache matching a pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys matching {pattern}")
        except Exception as e:
            logger.error(f"Redis CLEAR error: {str(e)}")
