"""
FastAPI Command Center API.
Main application entrypoint.

Architecture:
  Event Bus SQLite (source)
    → Projection Worker (PHASE 3.3)
    → PostgreSQL (read projections)
    → FastAPI (this API)
    → WebSocket (PHASE 3.5)
    → Frontend (PHASE 4)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core import settings
from ..database.connection import init_db
from .api.router import api_router

# Setup logging
logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context for FastAPI startup/shutdown.

    Startup: Initialize database schema
    Shutdown: Cleanup (if needed in future)
    """
    logger.info("Starting Command Center API...")
    try:
        init_db()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    logger.info("Shutting down Command Center API...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="REST API for NeoEve Command Center - Agent mission tracking and monitoring",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_router)


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """
    Lightweight health check.
    Returns 200 OK if API is running.
    """
    return {"status": "ok", "service": settings.APP_NAME}


@app.get(f"{settings.API_V1_STR}/health", tags=["health"])
async def health_check_detailed():
    """
    Detailed health check with component status.

    Returns health of:
    - API server
    - PostgreSQL connection
    - Projection Worker health (if available)
    """
    from ..database.connection import test_connection

    db_status = "connected"
    db_error = None

    try:
        result = test_connection()
        if not result:
            db_status = "unavailable"
            db_error = "No response from database"
    except Exception as e:
        db_status = "error"
        db_error = str(e)
        logger.warning(f"Database health check failed: {db_error}")

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "components": {
            "api": "healthy",
            "database": {
                "status": db_status,
                "error": db_error,
            },
        },
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
