import time

from app.cache.redis_client import redis_client
from app.security.rate_limiter_lua import SLIDING_WINDOW_LUA


class SlidingWindowRateLimiter:

    def __init__(self, prefix: str, max_requests: int, window_seconds: int):
        """
        Sliding window rate limiter.

        Args:
            prefix: namespace for redis keys
            max_requests: max allowed requests
            window_seconds: time window
        """

        self.prefix = prefix
        self.limit = max_requests
        self.window_ms = window_seconds * 1000

    def build_key(self, identifier: str):

        return f"ratelimit:{self.prefix}:{identifier}"

    def check(self, identifier: str):

        key = self.build_key(identifier)
        # print(key)

        now = int(time.time() * 1000)

        result = redis_client.eval(
            SLIDING_WINDOW_LUA,
            1,
            key,
            now,
            self.window_ms,
            self.limit,
        )

        count = int(result)

        remaining = max(self.limit - count, 0)

        return count, remaining, self.limit, self.window_ms