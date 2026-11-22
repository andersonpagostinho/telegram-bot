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

    # Database (SECURITY: No default credentials - must be set in environment)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # WebSocket Security
    WEBSOCKET_TICKET_TTL_MINUTES: int = int(os.getenv("WEBSOCKET_TICKET_TTL_MINUTES", "5"))
    WEBSOCKET_TICKET_RATE_LIMIT: int = int(os.getenv("WEBSOCKET_TICKET_RATE_LIMIT", "10"))  # Max 10 per minute per user
    WEBSOCKET_TICKET_RATE_WINDOW_SECONDS: int = 60  # Rate limit window in seconds

    # CORS
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080"
    ).split(",")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self, **data):
        super().__init__(**data)
        # Validate critical settings (SECURITY: Require environment variables in production)
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable is required. "
                "Set it in environment before running API."
            )
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Set it in environment before running API. "
                "Format: postgresql://user:password@host:port/dbname"
            )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
