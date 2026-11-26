"""API routes for Recovery Service dashboard and monitoring."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from app.services.recovery_metrics_service import RecoveryMetricsService
from app.core.security import get_current_user
from app.core.dependencies import verify_tenant_access

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get complete dashboard summary for recovery metrics."""
    # Verify tenant access
    await verify_tenant_access(current_user, tenant_id)

    summary = RecoveryMetricsService.get_dashboard_summary(db, tenant_id)
    return summary


@router.get("/metrics/total-recovered")
async def get_total_recovered(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get total number of executions recovered."""
    await verify_tenant_access(current_user, tenant_id)

    count = RecoveryMetricsService.get_total_recovered(db, tenant_id)
    return {"total_recovered": count, "tenant_id": tenant_id}


@router.get("/metrics/successful")
async def get_successful_recoveries(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get number of successful recoveries."""
    await verify_tenant_access(current_user, tenant_id)

    count = RecoveryMetricsService.get_successful_recoveries(db, tenant_id)
    return {"successful_recoveries": count, "tenant_id": tenant_id}


@router.get("/metrics/failed")
async def get_failed_recoveries(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get number of failed recoveries."""
    await verify_tenant_access(current_user, tenant_id)

    count = RecoveryMetricsService.get_failed_recoveries(db, tenant_id)
    return {"failed_recoveries": count, "tenant_id": tenant_id}


@router.get("/metrics/pending-retry")
async def get_pending_retry(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get executions awaiting retry."""
    await verify_tenant_access(current_user, tenant_id)

    count = RecoveryMetricsService.get_pending_retry_count(db, tenant_id)
    pending = RecoveryMetricsService.get_pending_executions(db, tenant_id)

    return {
        "pending_count": count,
        "pending_executions": [
            {
                "execution_id": p.execution_id,
                "mission_id": p.mission_id,
                "attempt_number": p.attempt_number,
                "next_retry_at": p.next_retry_at.isoformat() if p.next_retry_at else None,
            }
            for p in pending
        ],
        "tenant_id": tenant_id,
    }


@router.get("/metrics/failures-by-classification")
async def get_failures_by_classification(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get failure counts by classification (TRANSIENT, PERMANENT, UNKNOWN)."""
    await verify_tenant_access(current_user, tenant_id)

    failures = RecoveryMetricsService.get_failures_by_classification(db, tenant_id)
    return {"failures_by_classification": failures, "tenant_id": tenant_id}


@router.get("/metrics/average-recovery-time")
async def get_average_recovery_time(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get average recovery time in milliseconds."""
    await verify_tenant_access(current_user, tenant_id)

    avg_ms = RecoveryMetricsService.get_average_recovery_time(db, tenant_id)
    return {"average_recovery_time_ms": avg_ms, "tenant_id": tenant_id}


@router.get("/history/execution/{execution_id}")
async def get_execution_history(
    execution_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    limit: int = Query(50, description="Limit results"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recovery history (audit trail) for a specific execution."""
    await verify_tenant_access(current_user, tenant_id)

    history = RecoveryMetricsService.get_recovery_history(db, tenant_id, execution_id, limit)

    return {
        "execution_id": execution_id,
        "tenant_id": tenant_id,
        "attempts": [
            {
                "attempt_number": h.attempt_number,
                "worker_id": h.worker_id,
                "fencing_token": h.fencing_token,
                "failure_classification": h.failure_classification,
                "error_message": h.error_message,
                "attempted_at": h.attempted_at.isoformat(),
                "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                "duration_ms": h.duration_ms,
                "status": h.status,
                "next_retry_at": h.next_retry_at.isoformat() if h.next_retry_at else None,
            }
            for h in history
        ],
    }


@router.get("/history/recent-failures")
async def get_recent_failures(
    tenant_id: str = Query(..., description="Tenant ID"),
    hours: int = Query(24, description="Look back N hours"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recent failures in the last N hours."""
    await verify_tenant_access(current_user, tenant_id)

    failures = RecoveryMetricsService.get_recent_failures(db, tenant_id, hours)

    return {
        "tenant_id": tenant_id,
        "hours": hours,
        "count": len(failures),
        "failures": [
            {
                "execution_id": f.execution_id,
                "mission_id": f.mission_id,
                "failure_classification": f.failure_classification,
                "error_message": f.error_message,
                "attempted_at": f.attempted_at.isoformat(),
                "attempt_number": f.attempt_number,
            }
            for f in failures
        ],
    }


@router.get("/worker-health")
async def get_worker_health(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get health status per recovery worker."""
    await verify_tenant_access(current_user, tenant_id)

    health = RecoveryMetricsService.get_worker_health(db, tenant_id)
    return {"tenant_id": tenant_id, "workers": health}


@router.get("/status")
async def get_recovery_status(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get overall recovery status."""
    await verify_tenant_access(current_user, tenant_id)

    total = RecoveryMetricsService.get_total_recovered(db, tenant_id)
    successful = RecoveryMetricsService.get_successful_recoveries(db, tenant_id)
    failed = RecoveryMetricsService.get_failed_recoveries(db, tenant_id)
    pending = RecoveryMetricsService.get_pending_retry_count(db, tenant_id)

    success_rate = (successful / total * 100) if total > 0 else 0

    return {
        "tenant_id": tenant_id,
        "status": "operational" if pending > 0 else "idle",
        "total_attempts": total,
        "successful": successful,
        "failed": failed,
        "pending": pending,
        "success_rate_percent": success_rate,
    }
