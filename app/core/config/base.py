from pathlib import Path
import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class BaseConfig(BaseSettings):

    # -------------------------
    # Application
    # -------------------------
    APP_NAME: str = "Auth System"
    ENV: str = "development"
    DEBUG: bool = False

    BASE_URL: Optional[str] = None
    # -------------------------
    # Database
    # -------------------------
    DATABASE_URL: Optional[str] = None
    ADMIN_EMAIL: str = "admin@test.com"
    ADMIN_PASSWORD: str = "Admin@123"
    RP_ID: Optional[str] = None

    TEST_DATABASE_URL: str = "sqlite:///./test.db"

    # -------------------------
    # Redis
    # -------------------------
    REDIS_URL: Optional[str] = None

    OTEL_EXPORTER_ENDPOINT: Optional[str] = None
    # -------------------------
    # CORS
    # -------------------------
    ALLOWED_ORIGINS: str = "*"

    # -------------------------
    # SMTP
    # -------------------------
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    
    MAILTRAP_HOST: Optional[str] = None
    MAILTRAP_PORT: Optional[str] = None
    MAILTRAP_USERNAME: Optional[str] = None
    MAILTRAP_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None

    # -------------------------
    # JWT Configuration
    # -------------------------
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -------------------------
    # Security
    # -------------------------
    MAX_LOGIN_ATTEMPTS: int = 3
    LOCKOUT_MINUTES: int = 15

    # -------------------------
    # OTP Configuration
    # -------------------------
    OTP_EXPIRE_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RATE_LIMIT: int = 3
    OTP_RATE_LIMIT_WINDOW: int = 60
    
    # Global fallback rate limit
    RATE_LIMIT_PER_MINUTE: int = 60
    
    MFA_CHALLENGE_TTL: int = 300
    MFA_MAX_ATTEMPTS: int = 5
    
    # Google OAuth Configuration
    # -------------------------------
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"

    # ===============================
    # GITHUB OAUTH
    # ===============================

    AUTH_GITHUB_CLIENT_ID: Optional[str] = None
    AUTH_GITHUB_CLIENT_SECRET: Optional[str] = None

    GITHUB_OAUTH_URL: str = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL: str = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL: str = "https://api.github.com/user"
    GITHUB_USER_EMAIL_URL: str = "https://api.github.com/user/emails"
    
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None


    # -------------------------
    # JWT Keys
    # -------------------------
    
    @property
    def JWT_PRIVATE_KEY(self) -> str:
        # ✅ 1. Try ENV (Railway / Production)
        key = os.getenv("JWT_PRIVATE_KEY")
        if key:
            return key.replace("\\n", "\n")

        # ✅ 2. Fallback to file (Local)
        path = BASE_DIR / "keys/private.pem"
        if path.exists():
            return path.read_text()

        raise ValueError("JWT private key not found in ENV or file")


    @property
    def JWT_PUBLIC_KEY(self) -> str:
        # ✅ 1. Try ENV (Railway / Production)
        key = os.getenv("JWT_PUBLIC_KEY")
        if key:
            return key.replace("\\n", "\n")

        # ✅ 2. Fallback to file (Local)
        path = BASE_DIR / "keys/public.pem"
        if path.exists():
            return path.read_text()

        raise ValueError("JWT public key not found in ENV or file")
    # @property
    # def JWT_PRIVATE_KEY(self) -> str:
    #     path = BASE_DIR / "keys/private.pem"
    #     if not path.exists():
    #         raise FileNotFoundError("JWT private key not found")
    #     return path.read_text()

    # @property
    # def JWT_PUBLIC_KEY(self) -> str:
    #     path = BASE_DIR / "keys/public.pem"
    #     if not path.exists():
    #         raise FileNotFoundError("JWT public key not found")
    #     return path.read_text()

    # -------------------------
    # Rate Limiting Toggle
    # -------------------------
    RATE_LIMIT_ENABLED: bool = True

    # -------------------------
    # Environment Helpers
    # -------------------------
    
    @property
    def database_url(self):

        if self.ENV == "testing":
            return self.TEST_DATABASE_URL

        return self.DATABASE_URL
    
    @property
    def is_development(self):
        return self.ENV == "development"

    @property
    def is_testing(self):
        return self.ENV == "testing"

    @property
    def is_staging(self):
        return self.ENV == "staging"

    @property
    def is_production(self):
        return self.ENV == "production"

    # -------------------------
    # Pydantic Config
    # -------------------------
    model_config = ConfigDict(
        env_file=f".env.{os.getenv('ENV', 'development')}",
        extra="allow",
    )
    