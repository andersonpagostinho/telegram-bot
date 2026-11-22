"""
Database connection and session management.
PostgreSQL read projections for Command Center.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Test connections before using
    echo=False,  # Set True for SQL debugging
)

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
