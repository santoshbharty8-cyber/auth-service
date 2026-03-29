import logging
from contextlib import asynccontextmanager
from sqlalchemy import text

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles


from prometheus_client import make_asgi_app

from app.api import auth, admin, health, webauthn_router
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.observability.logging_config import setup_logging
from app.observability.request_logging_middleware import RequestLoggingMiddleware
from app.observability.request_id_middleware import RequestIDMiddleware
from app.observability.metrics_middleware import MetricsMiddleware
from app.observability.tracing import setup_tracing

import app.core.startup_state as startup_state
from app.core.database import engine
from app.core.config import settings


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting authentication service")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        startup_state.startup_complete = True
        logger.info("Database connected")

    except Exception:
        logger.exception("Database connection failed")

    yield

    logger.info("Shutting down authentication service")


app = FastAPI(
    title="Auth System",
    version="1.0.0",
    lifespan=lifespan,
    description=f"""
    🛡️ Admin Access

    Use the following credentials:

    Email:   admin@test.com
    Password: Admin@123


    🧪 Quick Demo

    🔐 Login
    1. POST `/auth/login`
    2. Copy `access_token`
    3. Click **Authorize**
    4. Call admin APIs:
    - `/admin/`
    - `/admin/roles`
    - `/admin/permissions`

    ---

    🔗 OAuth Login

    Login with Google:
        {settings.BASE_URL}/auth/oauth/google/login
    Login with GitHub: 
        {settings.BASE_URL}/auth/oauth/github/login
    
    🚀 Live Demo

    Open in browser:

    {settings.BASE_URL}/webauthn/demo

    ⚠️ WebAuthn cannot be tested inside Swagger

    ---

    ⚠️ Notes

    - Admin routes require `admin:access` / `admin:manage`
    - OAuth requires browser redirect (not Swagger)
    - Demo credentials only (not for production use)
    """
)

setup_tracing(app)


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
# app.mount("/tests", StaticFiles(directory="tests"), name="tests")



app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)


app.include_router(auth.router, prefix="/auth")
app.include_router(admin.router)
app.include_router(health.router)
app.include_router(webauthn_router.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    logger.exception(
        "Unhandled error",
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    logger.error(
        "validation_error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )