import logging
from sqlalchemy import text

from app.core.database import engine
from app.cache.redis_client import redis_client

logger = logging.getLogger(__name__)


def check_database() -> bool:
    """
    Lightweight DB health check using connection pool.
    Ensures DB is reachable without heavy overhead.
    """
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        return True

    except Exception:
        logger.exception("Database health check failed")
        return False


def check_redis() -> bool:
    """
    Redis health check using shared client.
    Avoids creating new connections per request.
    """
    try:
        return redis_client.ping()

    except Exception:
        logger.exception("Redis health check failed")
        return False