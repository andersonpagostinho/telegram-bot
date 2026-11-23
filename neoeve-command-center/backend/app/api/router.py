"""API router setup and registration."""

from fastapi import APIRouter

from .routes import agents, missions, tasks, executions, validations, metrics, events

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Register all route modules
api_router.include_router(agents.router)
api_router.include_router(missions.router)
api_router.include_router(tasks.router)
api_router.include_router(executions.router)
api_router.include_router(validations.router)
api_router.include_router(metrics.router)
api_router.include_router(events.router)
