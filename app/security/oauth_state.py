import secrets
from app.cache.redis_client import redis_client


STATE_EXPIRE = 300


def create_oauth_state():

    state = secrets.token_urlsafe(32)

    redis_client.setex(
        f"oauth_state:{state}",
        STATE_EXPIRE,
        "1"
    )

    return state


def validate_oauth_state(state: str):

    key = f"oauth_state:{state}"

    exists = redis_client.get(key)

    if not exists:
        return False

    redis_client.delete(key)

    return True