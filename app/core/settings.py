import os

from app.core.config.development import DevelopmentConfig
from app.core.config.testing import TestingConfig
from app.core.config.staging import StagingConfig
from app.core.config.production import ProductionConfig


ENV = os.getenv("ENV", "development")


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}


Settings = config_map.get(ENV, DevelopmentConfig)

settings = Settings()