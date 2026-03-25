import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.metrics import REQUEST_COUNT, REQUEST_LATENCY


class MetricsMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        start = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception:
            status_code = 500
            raise

        finally:

            duration = time.time() - start
            endpoint = request.url.path

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)

        return response