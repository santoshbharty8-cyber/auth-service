from .base import BaseConfig


class ProductionConfig(BaseConfig):

    ENV: str = "production"

    DEBUG: bool = False

    LOG_LEVEL: str = "WARNING"

    RATE_LIMIT_ENABLED: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15