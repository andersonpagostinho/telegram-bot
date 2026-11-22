"""
Configuration for FastAPI Command Center API.
Environment-based settings with secure defaults.
"""

import os
from datetime import timedelta

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """API configuration from environment variables."""

    # API
    APP_NAME: str = "NeoEve Command Center API"
    APP_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")  # Must be set in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"
    )

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self, **data):
        super().__init__(**data)
        # Validate critical settings
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable is required for production. "
                "Set it in environment before running API."
            )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
