import logging
import json
from redis.exceptions import RedisError
from jose import JWTError

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.security.jwt import decode_access_token
from app.security.rate_limiter import SlidingWindowRateLimiter
from app.security.rate_limit_policies import ENDPOINT_LIMITS
from app.observability.metrics import RATE_LIMIT_ERRORS, RATE_LIMIT_EXCEEDED

logger = logging.getLogger("security.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)

        # Global rate limiter
        self.global_limiter = SlidingWindowRateLimiter(
            prefix="global",
            max_requests=1000,
            window_seconds=60,
        )

        # Per-user limiter
        self.user_limiter = SlidingWindowRateLimiter(
            prefix="user",
            max_requests=100,
            window_seconds=60,
        )

        # Endpoint-specific limiters
        self.endpoint_limiters = {
            endpoint: SlidingWindowRateLimiter(
                prefix=config[0],
                max_requests=config[1],
                window_seconds=config[2],
            )
            for endpoint, config in ENDPOINT_LIMITS.items()
        }

    async def dispatch(self, request: Request, call_next):
        # print("🔥 RATE LIMIT MIDDLEWARE HIT:", request.url.path)
        # print("🚨 rate_limit_disabled:", getattr(request.app.state, "rate_limit_disabled", None))
        # print("🚨 settings.RATE_LIMIT_ENABLED:", settings.RATE_LIMIT_ENABLED)

        if self.rate_limit_disabled(request):
            return await call_next(request)

        ip = request.client.host if request.client else None
        path = request.url.path
        
        try:
            
            # Global limit
            response = self.check_global_limit(request, ip, path)
            if response:
                return response

            # Endpoint limits
            response = await self.check_endpoint_limit(request, path, ip)
            if response:
                return response

            # User limits
            response = self.check_user_limit(request, path)
            if response:
                return response

            return await call_next(request)

        except RedisError as exc:
            RATE_LIMIT_ERRORS.inc()

            logger.error(
                "rate_limiter_failure",
                extra={
                    "event": "rate_limiter_failure",
                    "path": path,
                    "request_id": getattr(request.state, "request_id", None),
                    "exception": str(exc),
                },
            )
            
            # Fail open if Redis is down
            return await call_next(request)

    # ---------------------------------
    # Disable rate limiting conditions
    # ---------------------------------

    def rate_limit_disabled(self, request: Request):

        if getattr(request.app.state, "rate_limit_disabled", False):
            return True

        if not settings.RATE_LIMIT_ENABLED:
            return True

        return False

    # ---------------------------------
    # Global rate limit
    # ---------------------------------

    def check_global_limit(self, request, ip, path):

        count, remaining, limit, window = self.global_limiter.check(ip)

        if count >= limit:
            
            RATE_LIMIT_EXCEEDED.labels(
                type="global",
                endpoint="global"
            ).inc()

            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "event": "rate_limit_exceeded",
                    "type": "global",
                    "client_ip": ip,
                    "path": path,
                    "limit": limit,
                    "window_ms": window,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
            
            return self.limit_response(
                "Global API rate limit exceeded",
                limit,
                remaining,
                window,
            )

        return None

    # ---------------------------------
    # Endpoint-specific rate limits
    # ---------------------------------

    async def check_endpoint_limit(self, request, path, ip):

        for endpoint, limiter in self.endpoint_limiters.items():

            if not path.startswith(endpoint):
                continue

            identifier = await self.extract_identifier(ip)

            count, remaining, limit, window = limiter.check(identifier)
            # print(f"📊 LIMIT CHECK → id={identifier}, count={count}, limit={limit}")

            if count >= limit:
                
                RATE_LIMIT_EXCEEDED.labels(
                    type="endpoint",
                    endpoint=endpoint
                ).inc()

                logger.warning(
                    "rate_limit_exceeded",
                    extra={
                        "event": "rate_limit_exceeded",
                        "type": "endpoint",
                        "endpoint": endpoint,
                        "identifier": identifier,
                        "path": path,
                        "limit": limit,
                        "window_ms": window,
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
                
                return self.limit_response(
                    f"Rate limit exceeded for {endpoint}",
                    limit,
                    remaining,
                    window,
                )

        return None

    # ---------------------------------
    # Extract identifier (IP or email)
    # ---------------------------------

    async def extract_identifier(self, ip):
        
        return ip

    # ---------------------------------
    # Per-user rate limit
    # ---------------------------------

    def check_user_limit(self, request, path):

        user_id = self.get_user_id(request)

        if not user_id:
            return None

        count, remaining, limit, window = self.user_limiter.check(user_id)

        if count >= limit:
            
            RATE_LIMIT_EXCEEDED.labels(
                type="user",
                endpoint=path
            ).inc()

            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "event": "rate_limit_exceeded",
                    "type": "user",
                    "user_id": user_id,
                    "path": path,
                    "limit": limit,
                    "window_ms": window,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
            
            return self.limit_response(
                "User API rate limit exceeded",
                limit,
                remaining,
                window,
            )

        return None

    # ---------------------------------
    # Extract user ID from JWT
    # ---------------------------------

    def get_user_id(self, request: Request):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        try:

            token = auth_header.split(" ")[1]

            payload = decode_access_token(token)

            return payload.get("sub")

        except (JWTError, IndexError):
            return None

    # ---------------------------------
    # Rate limit response
    # ---------------------------------

    def limit_response(self, message, limit, remaining, window):

        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": message,
                "limit": limit,
                "remaining": remaining,
                "window_ms": window,
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Window": str(window),
            },
        )