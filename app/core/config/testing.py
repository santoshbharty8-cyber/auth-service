from .base import BaseConfig


class TestingConfig(BaseConfig):

    ENV: str = "testing"

    DEBUG: bool = True

    LOG_LEVEL: str = "DEBUG"

    RATE_LIMIT_ENABLED: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5