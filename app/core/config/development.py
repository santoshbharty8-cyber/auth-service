from .base import BaseConfig


class DevelopmentConfig(BaseConfig):

    ENV: str = "development"

    DEBUG: bool = True

    LOG_LEVEL: str = "DEBUG"

    RATE_LIMIT_ENABLED: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60