"""Redis-backed sliding-window rate limiter.

Protects the API from abuse and prevents free-tier credit burnout.
"""
import time
import redis
from fastapi import Request, HTTPException
from config import settings


# Lazy-init Redis client (separate from Celery's connection)
_redis_client = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


class RateLimiter:
    """Sliding-window rate limiter using Redis INCR + EXPIRE."""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Returns:
            (allowed: bool, current_count: int, retry_after: int)
        """
        r = get_redis_client()
        now = int(time.time())
        window = now // self.window_seconds
        redis_key = f"rate_limit:{key}:{window}"

        pipe = r.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, self.window_seconds)
        results = pipe.execute()

        count = results[0]
        allowed = count <= self.max_requests
        retry_after = self.window_seconds - (now % self.window_seconds)

        return allowed, count, retry_after


# ── Pre-configured limiters ──────────────────────────────────────────────
job_submission_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_PER_MIN)
job_poll_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_POLL_PER_MIN)
job_list_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_LIST_PER_MIN)
job_revoke_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_PER_MIN)


# ── Helpers ────────────────────────────────────────────────────────────────
def _get_client_ip(request: Request) -> str:
    """Extract real client IP behind Render proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── FastAPI dependencies ─────────────────────────────────────────────────
def rate_limit_post_jobs(request: Request):
    ip = _get_client_ip(request)
    allowed, count, retry_after = job_submission_limiter.is_allowed(f"{ip}:post_jobs")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({count} requests). Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_get_job(request: Request):
    ip = _get_client_ip(request)
    allowed, count, retry_after = job_poll_limiter.is_allowed(f"{ip}:get_job")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({count} requests). Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_list_jobs(request: Request):
    ip = _get_client_ip(request)
    allowed, count, retry_after = job_list_limiter.is_allowed(f"{ip}:list_jobs")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({count} requests). Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_revoke_job(request: Request):
    ip = _get_client_ip(request)
    allowed, count, retry_after = job_revoke_limiter.is_allowed(f"{ip}:revoke_job")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({count} requests). Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )