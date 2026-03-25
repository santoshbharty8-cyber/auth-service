import redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,

            # TIMEOUTS (VERY IMPORTANT)
            socket_connect_timeout=2,
            socket_timeout=2,

            # CONNECTION POOL
            max_connections=50,

            # RETRY ON FAILURE
            retry_on_timeout=True
        )

        return client

    except Exception:
        logger.exception("Failed to create Redis client")
        raise


# Global reusable client
redis_client = get_redis_client()