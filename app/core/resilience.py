import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, TypeVar, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Rate Limit Registry to share state across decorators for the same service
SERVICE_RATE_LIMITS: Dict[str, Dict[str, Any]] = {}

def rate_limit(service_name: str, requests_per_minute: int = 5):
    """
    Very simple async rate limiter decorator using asyncio.sleep.
    Adjusts to ensure a minimum gap between requests.
    """
    if service_name not in SERVICE_RATE_LIMITS:
        SERVICE_RATE_LIMITS[service_name] = {
            "last_request_time": 0.0,
            "min_gap": 60.0 / requests_per_minute
        }

    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            limit_data = SERVICE_RATE_LIMITS[service_name]
            now = time.time()
            elapsed = now - limit_data["last_request_time"]
            
            if elapsed < limit_data["min_gap"]:
                sleep_time = limit_data["min_gap"] - elapsed
                logger.info(f"Rate limiting {service_name}: sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
            
            limit_data["last_request_time"] = time.time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def retry_http_request(
    max_attempts: int = 3, 
    min_wait: int = 1, 
    max_wait: int = 10
):
    """
    Retry logic for HTTP 5xx or transient connection errors.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

def handle_gemini_quota(func: Callable[..., Any]):
    """
    Special handling for Gemini 429 errors.
    """
    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, max=60),
        retry=retry_if_exception_type(Exception), # LangChain wraps these in generic or specific exceptions
        # We need to be careful not to retry permanent errors
        before_sleep=before_sleep_log(logger, logging.ERROR),
        reraise=True
    )
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                logger.warning(f"Gemini Quota Exceeded. Retrying... Error: {e}")
                raise e # Trigger tenacity retry
            raise e
    return wrapper
