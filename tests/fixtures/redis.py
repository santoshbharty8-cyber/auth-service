import pytest
from app.cache.redis_client import redis_client as _redis_client


@pytest.fixture
def redis_client():
    return _redis_client