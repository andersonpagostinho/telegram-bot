"""Recovery Metrics Service: operational monitoring for RecoveryService."""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import RecoveryMetrics, RecoveryHistory, utc_now
from app.services.recovery_service import FailureClassification

logger = logging.getLogger(__name__)


class RecoveryMetricsService:
    """Collect and retrieve metrics for Recovery operation monitoring."""

    @staticmethod
    def record_recovery_attempt(
        db: Session,
        execution_id: str,
        mission_id: str,
        task_id: str,
        tenant_id: str,
        attempt_number: int,
        worker_id: str,
        fencing_token: int,
        failure_classification: str,
        error_message: str,
        status: str,
        duration_ms: int,
        next_retry_at: datetime = None,
    ) -> None:
        """Record a single recovery attempt in history."""
        history = RecoveryHistory(
            execution_id=execution_id,
            mission_id=mission_id,
            task_id=task_id,
            tenant_id=tenant_id,
            attempt_number=attempt_number,
            worker_id=worker_id,
            fencing_token=fencing_token,
            failure_classification=failure_classification,
            error_message=error_message,
            attempted_at=utc_now(),
            completed_at=utc_now() if status == "COMPLETED" else None,
            duration_ms=duration_ms,
            status=status,
            next_retry_at=next_retry_at,
        )
        db.add(history)
        db.commit()

    @staticmethod
    def get_total_recovered(db: Session, tenant_id: str) -> int:
        """Get total number of executions recovered (all attempts)."""
        count = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status.in_(["COMPLETED", "FAILED"])
        ).count()
        return count

    @staticmethod
    def get_successful_recoveries(db: Session, tenant_id: str) -> int:
        """Get number of successful recoveries."""
        count = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status == "COMPLETED"
        ).count()
        return count

    @staticmethod
    def get_failed_recoveries(db: Session, tenant_id: str) -> int:
        """Get number of permanent failures (not retried)."""
        count = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status == "FAILED",
            RecoveryHistory.failure_classification == FailureClassification.PERMANENT
        ).count()
        return count

    @staticmethod
    def get_pending_retry_count(db: Session, tenant_id: str) -> int:
        """Get executions awaiting retry."""
        count = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status == "QUEUED",
            RecoveryHistory.next_retry_at > utc_now()
        ).count()
        return count

    @staticmethod
    def get_pending_executions(db: Session, tenant_id: str):
        """Get list of executions awaiting retry."""
        return db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status == "QUEUED",
            RecoveryHistory.next_retry_at > utc_now()
        ).order_by(RecoveryHistory.next_retry_at).all()

    @staticmethod
    def get_failures_by_classification(db: Session, tenant_id: str) -> dict:
        """Get failure counts by classification."""
        results = db.query(
            RecoveryHistory.failure_classification,
            func.count(RecoveryHistory.id).label("count")
        ).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status == "FAILED"
        ).group_by(RecoveryHistory.failure_classification).all()

        return {
            result[0]: result[1]
            for result in results
        }

    @staticmethod
    def get_average_recovery_time(db: Session, tenant_id: str) -> float:
        """Get average recovery time in milliseconds."""
        avg_duration = db.query(func.avg(RecoveryHistory.duration_ms)).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status.in_(["COMPLETED", "FAILED"])
        ).scalar()

        return avg_duration or 0.0

    @staticmethod
    def get_recovery_history(
        db: Session,
        tenant_id: str,
        execution_id: str = None,
        limit: int = 50
    ):
        """Get recovery history (audit trail) for an execution or all."""
        query = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id
        )

        if execution_id:
            query = query.filter(RecoveryHistory.execution_id == execution_id)

        return query.order_by(RecoveryHistory.attempted_at.desc()).limit(limit).all()

    @staticmethod
    def get_recent_failures(db: Session, tenant_id: str, hours: int = 24) -> list:
        """Get failures in the last N hours."""
        cutoff = utc_now() - timedelta(hours=hours)

        return db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.status == "FAILED",
            RecoveryHistory.attempted_at > cutoff
        ).order_by(RecoveryHistory.attempted_at.desc()).all()

    @staticmethod
    def get_worker_health(db: Session, tenant_id: str) -> dict:
        """Get health status per worker."""
        results = db.query(
            RecoveryHistory.worker_id,
            func.count(RecoveryHistory.id).label("total"),
            func.count(func.nullif(RecoveryHistory.status == "COMPLETED", False)).label("successful")
        ).filter(
            RecoveryHistory.tenant_id == tenant_id
        ).group_by(RecoveryHistory.worker_id).all()

        health = {}
        for worker_id, total, successful in results:
            if worker_id:
                health[worker_id] = {
                    "total_attempts": total,
                    "successful": successful or 0,
                    "success_rate": ((successful or 0) / total * 100) if total > 0 else 0
                }

        return health

    @staticmethod
    def cleanup_old_history(db: Session, tenant_id: str, days: int = 30) -> int:
        """Remove recovery history older than N days (cleanup task)."""
        cutoff = utc_now() - timedelta(days=days)

        count = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id,
            RecoveryHistory.attempted_at < cutoff
        ).delete()

        db.commit()
        return count

    @staticmethod
    def get_dashboard_summary(db: Session, tenant_id: str) -> dict:
        """Get complete dashboard summary for tenant."""
        return {
            "tenant_id": tenant_id,
            "total_recovered": RecoveryMetricsService.get_total_recovered(db, tenant_id),
            "successful_recoveries": RecoveryMetricsService.get_successful_recoveries(db, tenant_id),
            "failed_recoveries": RecoveryMetricsService.get_failed_recoveries(db, tenant_id),
            "pending_retry_count": RecoveryMetricsService.get_pending_retry_count(db, tenant_id),
            "failures_by_classification": RecoveryMetricsService.get_failures_by_classification(db, tenant_id),
            "average_recovery_time_ms": RecoveryMetricsService.get_average_recovery_time(db, tenant_id),
            "worker_health": RecoveryMetricsService.get_worker_health(db, tenant_id),
            "timestamp": utc_now().isoformat(),
        }
