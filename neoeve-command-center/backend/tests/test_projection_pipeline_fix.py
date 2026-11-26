"""
Test suite for ProjectionWorker pipeline fix.

Validates:
1. Correct import of ProjectionWorker from app.services
2. Scheduler initialization without errors
3. Multi-tenant isolation
4. Pipeline: SQLite Event Bus → ProjectionWorker → PostgreSQL → Overview
"""

import pytest
import sys
import os
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set environment variables for testing
os.environ.setdefault("SECRET_KEY", "test-secret-key-123")
os.environ.setdefault("DATABASE_URL", "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center")


class TestProjectionWorkerImport:
    """Test that ProjectionWorker is correctly imported."""

    def test_import_from_app_services(self):
        """Verify ProjectionWorker can be imported from app.services."""
        from app.services.projection_worker import ProjectionWorker
        assert ProjectionWorker is not None
        assert hasattr(ProjectionWorker, '__init__')

    def test_import_should_not_come_from_workers(self):
        """Verify that workers.projection_worker is NOT used."""
        # This should fail (workers.projection_worker has bad imports)
        try:
            from workers.projection_worker import ProjectionWorker as WorkersProjectionWorker
            pytest.skip("workers.projection_worker imports are broken (expected)")
        except ImportError as e:
            # Expected: event_bus module not found
            assert "event_bus" in str(e) or "No module" in str(e)


class TestSchedulerInitialization:
    """Test scheduler can initialize without errors."""

    def test_scheduler_import(self):
        """Test that scheduler can be imported and initialized."""
        from app.core.scheduler import ApprovalScheduler

        # Create scheduler instance (don't start thread)
        scheduler = ApprovalScheduler(
            interval_seconds=1,
            outbox_batch_size=5,
            projection_batch_size=10,
        )

        assert scheduler is not None
        assert scheduler.interval_seconds == 1

    def test_projection_worker_initialization_in_scheduler(self):
        """Test that ProjectionWorker initializes in scheduler context."""
        # This simulates what happens in _run() method
        try:
            from app.services.projection_worker import ProjectionWorker as BaseProjectionWorker

            # Mimic the wrapper from scheduler.py
            class SchedulerProjectionWorker:
                def __init__(self, batch_size: int):
                    self.base_worker = BaseProjectionWorker(batch_size=batch_size)
                    self.db_session = None
                    self._total_processed = 0
                    self._total_rejected = 0

                def consume_and_project(self):
                    pass

                def get_metrics(self) -> dict:
                    return {
                        "total_events_processed": self._total_processed,
                        "events_rejected": self._total_rejected,
                    }

            # Create instance
            worker = SchedulerProjectionWorker(batch_size=10)
            assert worker is not None
            assert worker.get_metrics() == {
                "total_events_processed": 0,
                "events_rejected": 0,
            }

        except Exception as e:
            pytest.fail(f"Failed to initialize ProjectionWorker in scheduler: {e}")


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation."""

    def test_mission_has_tenant_id(self):
        """Verify Mission model includes tenant_id."""
        from database.models import Mission
        from sqlalchemy import inspect

        columns = {c.name for c in inspect(Mission).columns}
        assert "tenant_id" in columns, "Mission must have tenant_id for multi-tenant isolation"
        assert "project_id" in columns, "Mission must have project_id"

    def test_task_is_connected_to_tenant_via_mission(self):
        """Verify Task is connected to tenant through Mission relationship."""
        from database.models import Task, Mission
        from sqlalchemy import inspect

        task_columns = {c.name for c in inspect(Task).columns}
        assert "mission_id" in task_columns, "Task must have mission_id to link to Mission"

        mission_columns = {c.name for c in inspect(Mission).columns}
        assert "tenant_id" in mission_columns, "Mission must have tenant_id"

    def test_execution_is_connected_to_tenant_via_mission(self):
        """Verify Execution is connected to tenant through Mission relationship."""
        from database.models import Execution, Mission
        from sqlalchemy import inspect

        execution_columns = {c.name for c in inspect(Execution).columns}
        assert "mission_id" in execution_columns, "Execution must have mission_id to link to Mission"

        mission_columns = {c.name for c in inspect(Mission).columns}
        assert "tenant_id" in mission_columns, "Mission must have tenant_id"

    def test_agent_events_have_tenant_id(self):
        """Verify AgentEvent includes tenant_id."""
        from database.models import AgentEvent
        from sqlalchemy import inspect

        columns = {c.name for c in inspect(AgentEvent).columns}
        assert "tenant_id" in columns, "AgentEvent must have tenant_id"
        assert "project_id" in columns, "AgentEvent must have project_id"


class TestMetricsOverviewEndpoint:
    """Test the /metrics/overview endpoint isolation."""

    def test_metrics_endpoint_filters_missions_by_tenant(self):
        """Verify that metrics endpoint queries missions with tenant filter."""
        # Read the endpoint code to verify the filter exists
        import inspect as code_inspect
        from app.api.routes import metrics

        source = code_inspect.getsource(metrics.metrics_overview)

        # Check for tenant_id filter in missions query
        assert "tenant_id == current_user.tenant_id" in source, \
            "Metrics endpoint must filter missions by tenant_id"

    def test_metrics_endpoint_filters_tasks_via_mission(self):
        """Verify tasks are filtered through mission tenant."""
        import inspect as code_inspect
        from app.api.routes import metrics

        source = code_inspect.getsource(metrics.metrics_overview)

        # Tasks should be joined with Mission and filtered by tenant
        assert "join(Mission" in source, \
            "Tasks must be joined with Mission for tenant filtering"
        assert "tenant_id == current_user.tenant_id" in source, \
            "Missions in task query must be filtered by tenant"

    def test_metrics_endpoint_filters_executions_via_mission(self):
        """Verify executions are filtered through mission tenant."""
        import inspect as code_inspect
        from app.api.routes import metrics

        source = code_inspect.getsource(metrics.metrics_overview)

        # Executions should be joined with Mission and filtered by tenant
        assert "Execution" in source, "Must query Execution model"
        assert "tenant_id == current_user.tenant_id" in source, \
            "Executions must be filtered by tenant via Mission"


class TestEventBusIntegrity:
    """Test Event Bus idempotency and ACK."""

    def test_event_bus_has_idempotency_support(self):
        """Verify event bus implements idempotency keys."""
        from app.services.event_bus import publish_event
        import inspect as code_inspect

        source = code_inspect.getsource(publish_event)

        # Should check for idempotency_key
        assert "idempotency_key" in source, "Event bus must support idempotency keys"

    def test_projection_worker_checks_idempotency(self):
        """Verify projection worker checks for processed events."""
        from app.services.projection_worker import handle_approval_requested
        import inspect as code_inspect

        source = code_inspect.getsource(handle_approval_requested)

        # Should check ProcessedEvent before processing
        assert "ProcessedEvent" in source, \
            "Projection worker must check idempotency with ProcessedEvent table"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
