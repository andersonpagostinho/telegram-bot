"""Metrics endpoints for dashboard and monitoring."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import get_db, get_current_user, Identity
from database.models import Agent, Mission, Task, Execution, AgentEvent, ProjectionCheckpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview")
async def metrics_overview(
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get system overview metrics.

    Returns real data from PostgreSQL projections.

    NOTE: Agents are GLOBAL system resources (not tenant-scoped).
    Missions, Tasks, and Executions are filtered by current_user.tenant_id.
    """
    try:
        # Count agents by status (GLOBAL - not tenant-specific)
        total_agents = db.query(func.count(Agent.agent_id)).scalar() or 0
        active_agents = (
            db.query(func.count(Agent.agent_id))
            .filter(Agent.status == "WORKING")
            .scalar() or 0
        )

        # Count missions for tenant
        total_missions = (
            db.query(func.count(Mission.mission_id))
            .filter(Mission.tenant_id == current_user.tenant_id)
            .scalar() or 0
        )

        completed_missions = (
            db.query(func.count(Mission.mission_id))
            .filter(
                Mission.tenant_id == current_user.tenant_id,
                Mission.status == "COMPLETED",
            )
            .scalar() or 0
        )

        # Count tasks
        total_tasks = (
            db.query(func.count(Task.task_id))
            .join(Mission, Task.mission_id == Mission.mission_id)
            .filter(Mission.tenant_id == current_user.tenant_id)
            .scalar() or 0
        )

        # Count executions (last 7 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_executions = (
            db.query(func.count(Execution.execution_id))
            .join(Mission, Execution.mission_id == Mission.mission_id)
            .filter(
                Mission.tenant_id == current_user.tenant_id,
                Execution.queued_at >= cutoff,
            )
            .scalar() or 0
        )

        logger.info(
            f"Overview metrics retrieved for tenant={current_user.tenant_id} "
            f"(user={current_user.user_id})"
        )

        return {
            "agents": {
                "total": total_agents,
                "active": active_agents,
            },
            "missions": {
                "total": total_missions,
                "completed": completed_missions,
                "completion_rate": (
                    (completed_missions / total_missions * 100) if total_missions > 0 else 0
                ),
            },
            "tasks": {
                "total": total_tasks,
            },
            "executions_7d": recent_executions,
        }
    except Exception as e:
        logger.error(f"Error retrieving overview metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


@router.get("/agents")
async def metrics_agents(
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """Get per-agent statistics."""
    try:
        agents = db.query(Agent).all()

        agent_metrics = []
        for agent in agents:
            # Count executions for this agent (last 7 days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            execution_count = (
                db.query(func.count(Execution.execution_id))
                .filter(
                    Execution.agent_id == agent.agent_id,
                    Execution.queued_at >= cutoff,
                )
                .scalar() or 0
            )

            agent_metrics.append({
                "agent_id": agent.agent_id,
                "role": agent.agent_role,
                "status": agent.status,
                "last_activity": agent.last_execution_at,
                "executions_7d": execution_count,
            })

        logger.info(f"Agent metrics retrieved for user={current_user.user_id}")

        return {"agents": agent_metrics}
    except Exception as e:
        logger.error(f"Error retrieving agent metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


@router.get("/missions")
async def metrics_missions(
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """Get mission progress metrics for tenant."""
    try:
        # Mission status breakdown
        status_counts = (
            db.query(Mission.status, func.count(Mission.mission_id))
            .filter(Mission.tenant_id == current_user.tenant_id)
            .group_by(Mission.status)
            .all()
        )

        total_missions = sum(count for _, count in status_counts)
        status_breakdown = {status: count for status, count in status_counts}

        # Average mission duration (completed only)
        avg_duration = (
            db.query(
                func.avg(
                    func.extract(
                        "epoch",
                        Mission.completed_at - Mission.started_at,
                    )
                )
            )
            .filter(
                Mission.tenant_id == current_user.tenant_id,
                Mission.status == "COMPLETED",
                Mission.started_at.isnot(None),
                Mission.completed_at.isnot(None),
            )
            .scalar()
        )

        logger.info(f"Mission metrics retrieved for tenant={current_user.tenant_id}")

        return {
            "total": total_missions,
            "by_status": status_breakdown,
            "avg_duration_seconds": avg_duration or 0,
        }
    except Exception as e:
        logger.error(f"Error retrieving mission metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


@router.get("/projection-worker")
async def metrics_projection_worker(
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get Projection Worker health and metrics.

    Returns checkpoint status and event processing metrics.
    """
    try:
        # Get worker checkpoint
        checkpoint = (
            db.query(ProjectionCheckpoint)
            .filter(ProjectionCheckpoint.consumer_id == "projection-worker")
            .first()
        )

        if not checkpoint:
            return {
                "status": "unknown",
                "error": "No checkpoint found",
            }

        # Count total events in PostgreSQL
        total_events = db.query(func.count(AgentEvent.event_id)).scalar() or 0

        logger.info(f"Projection Worker metrics retrieved (user={current_user.user_id})")

        return {
            "status": checkpoint.status,
            "last_processed_event_id": checkpoint.last_processed_event_id,
            "last_processed_at": checkpoint.last_processed_at,
            "error_count": checkpoint.error_count,
            "updated_at": checkpoint.updated_at,
            "total_events_projected": total_events,
        }
    except Exception as e:
        logger.error(f"Error retrieving Projection Worker metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


@router.get("/scheduler")
async def metrics_scheduler(
    current_user: Identity = Depends(get_current_user),
):
    """
    Get Approval Scheduler status and metrics.

    ETAPA 4: Scheduler automation for Outbox Publisher, Recovery, and Projection Worker.
    Returns:
    - Scheduler status (running/stopped)
    - Total runs and last execution time
    - Counts of published Outbox events, recovered events, projected events
    - Error count
    """
    try:
        from app.core.scheduler import get_scheduler

        scheduler = get_scheduler()

        if not scheduler:
            return {
                "status": "not_running",
                "error": "Scheduler not initialized",
            }

        metrics = scheduler.get_metrics()

        logger.info(f"Scheduler metrics retrieved (user={current_user.user_id})")

        return {
            "status": "running",
            "total_runs": metrics.get("total_runs", 0),
            "last_run_at": metrics.get("last_run_at"),
            "outbox_published": metrics.get("outbox_published", 0),
            "outbox_failed": metrics.get("outbox_failed", 0),
            "events_recovered": metrics.get("events_recovered", 0),
            "events_projected": metrics.get("events_projected", 0),
            "errors": metrics.get("errors", 0),
        }
    except Exception as e:
        logger.error(f"Error retrieving Scheduler metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scheduler metrics",
        )
