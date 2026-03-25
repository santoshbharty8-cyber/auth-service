from app.cache.redis_client import redis_client


def blacklist_token(jti: str, ttl_seconds: int):
    redis_client.set(
        f"blacklist:{jti}",
        "revoked",
        ex=ttl_seconds
    )


def is_token_blacklisted(jti: str) -> bool:
    return redis_client.get(f"blacklist:{jti}") is not None