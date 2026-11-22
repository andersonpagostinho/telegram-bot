"""
Database connection and session management.
PostgreSQL read projections for Command Center.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"
)

# Create engine with connection pooling
# Allow graceful fallback if PostgreSQL unavailable (for testing)
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Test connections before using
        echo=False,  # Set True for SQL debugging
    )
except Exception as e:
    logger.warning(f"PostgreSQL not available ({type(e).__name__}). Using SQLite fallback for testing.")
    engine = create_engine("sqlite:///:memory:")

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from .models import Base
    Base.metadata.create_all(bind=engine)


def test_connection():
    """Test database connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            return result.fetchone()
    except Exception as e:
        return None
