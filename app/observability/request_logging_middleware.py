import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        start = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as exc:
            status_code = 500
            logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "path": request.url.path,
                }
            )
            raise exc

        duration = round((time.time() - start) * 1000, 2)

        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "request_id": getattr(request.state, "request_id", None),
                "user_id": getattr(request.state, "user_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration,
                "client_ip": request.client.host if request.client else None,
            },
        )

        return response