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
from database.connection import init_db
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

    Startup:
    - Initialize database schema
    - Start Approval Scheduler for Outbox Publisher, Recovery, and Projection Worker

    Shutdown:
    - Stop Approval Scheduler gracefully
    """
    logger.info("Starting Command Center API...")
    try:
        init_db()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Start Approval Scheduler
    try:
        from .core.scheduler import init_scheduler
        scheduler = init_scheduler(
            interval_seconds=10,  # Run every 10 seconds
            outbox_batch_size=10,
            projection_batch_size=50,
        )
        logger.info("Approval Scheduler started")
        app.state.scheduler = scheduler
    except Exception as e:
        logger.error(f"Failed to start Approval Scheduler: {e}")
        # Non-fatal: continue even if scheduler fails
        app.state.scheduler = None

    # Verify Claude Code subscription (startup diagnostics)
    try:
        from .services.claude_code_adapter import ClaudeCodeAdapter
        from app.services.agent_registry import AgentRegistry, ConnectivityState
        from database.connection import get_db

        adapter = ClaudeCodeAdapter(subscription_only=True)
        health = adapter.health_check()

        if health["cli_available"]:
            logger.info("✓ Claude Code CLI available")
            if health["subscription_valid"]:
                logger.info("✓ Claude Pro subscription verified")
                app.state.claude_auth_status = "ONLINE"

                # PHASE 1: Mark all agents ONLINE only after successful health check
                # Health check must pass BOTH: CLI available AND subscription valid
                try:
                    db = next(get_db())
                    for key, agent_config in AgentRegistry.AGENTS.items():
                        agent_id = agent_config["agent_id"]
                        success = AgentRegistry.update_connectivity_state(
                            db, agent_id, ConnectivityState.ONLINE
                        )
                        if success:
                            logger.info(f"Agent {agent_id} marked ONLINE (health check passed)")
                        else:
                            logger.warning(f"Agent {agent_id} not found in database")
                    db.close()
                except Exception as hc_err:
                    logger.error(f"Failed to update agent connectivity during startup: {hc_err}")
            else:
                logger.warning("⚠ Claude Code CLI found but subscription not valid")
                logger.warning(f"  Reason: {health['subscription_status'].get('error', 'unknown')}")
                app.state.claude_auth_status = "AUTH_REQUIRED"
        else:
            logger.warning("⚠ Claude Code CLI not available")
            if health["errors"]:
                logger.warning(f"  Errors: {'; '.join(health['errors'])}")
            app.state.claude_auth_status = "OFFLINE"
    except Exception as e:
        logger.warning(f"⚠ Could not verify Claude Code authentication: {e}")
        app.state.claude_auth_status = "UNKNOWN"

    yield

    # Stop Approval Scheduler
    try:
        if hasattr(app.state, "scheduler") and app.state.scheduler:
            from .core.scheduler import stop_scheduler
            stop_scheduler()
            logger.info("Approval Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping Approval Scheduler: {e}")

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
    from database.connection import test_connection

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
