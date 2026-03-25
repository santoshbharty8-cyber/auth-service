from .base import BaseConfig


class StagingConfig(BaseConfig):

    ENV: str = "staging"

    DEBUG: bool = False

    LOG_LEVEL: str = "INFO"

    RATE_LIMIT_ENABLED: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30