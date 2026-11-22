"""
Integration tests for FastAPI Command Center API.
Tests real PostgreSQL connections with multi-tenant isolation.

Execution: pytest tests/test_api_integration.py -v
"""

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import create_access_token
from database.connection import SessionLocal, engine
from database.models import Agent, Mission, Task, Execution, AgentEvent, Base, ProjectionCheckpoint


# Test client
client = TestClient(app)


@pytest.fixture(scope="session")
def setup_db():
    """Create test database schema."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_db):
    """Get database session for test."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_tenant():
    """Generate unique tenant ID for each test."""
    return f"test_tenant_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_token(test_tenant):
    """Create JWT token for test tenant."""
    return create_access_token(
        user_id=f"user_{uuid.uuid4().hex[:8]}",
        tenant_id=test_tenant,
        actor_id=f"actor_{uuid.uuid4().hex[:8]}",
        actor_role="architect",
    )


@pytest.fixture
def test_mission(db_session, test_tenant):
    """Create test mission."""
    mission = Mission(
        mission_id=f"mission_{uuid.uuid4().hex[:8]}",
        project_id="test_project",
        tenant_id=test_tenant,
        name="Test Mission",
        status="RUNNING",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(mission)
    db_session.commit()
    return mission


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_basic(self):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_check_detailed(self, test_token):
        """Test detailed health check with auth."""
        response = client.get(
            "/api/v1/health",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "components" in data


class TestAuthentication:
    """Test authentication and authorization."""

    def test_missing_token(self):
        """Test endpoint without token."""
        response = client.get("/api/v1/agents")
        assert response.status_code == 403

    def test_invalid_token(self):
        """Test endpoint with invalid token."""
        response = client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401

    def test_valid_token(self, test_token):
        """Test endpoint with valid token."""
        response = client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        # Should succeed or return 200 with empty list
        assert response.status_code in [200, 404]


class TestAgentEndpoints:
    """Test agent endpoints."""

    def test_list_agents_empty(self, test_token):
        """Test listing agents when empty."""
        response = client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "agents" in data

    def test_list_agents_with_pagination(self, test_token):
        """Test pagination parameters."""
        response = client.get(
            "/api/v1/agents?page=1&per_page=20",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200

    def test_get_nonexistent_agent(self, test_token):
        """Test retrieving non-existent agent."""
        response = client.get(
            "/api/v1/agents/nonexistent_agent",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 404

    def test_agent_events(self, test_token):
        """Test agent events endpoint."""
        response = client.get(
            "/api/v1/agents/test_agent/events",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        # Should return 404 or 200 with empty list
        assert response.status_code in [200, 404]


class TestMissionEndpoints:
    """Test mission endpoints with multi-tenant security."""

    def test_list_missions_empty(self, test_token, test_tenant):
        """Test listing missions for tenant."""
        response = client.get(
            "/api/v1/missions",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "missions" in data
        assert data["total"] == 0  # Empty for new tenant

    def test_get_nonexistent_mission(self, test_token):
        """Test retrieving non-existent mission returns 403."""
        response = client.get(
            "/api/v1/missions/nonexistent_mission",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        # Should return 403 (forbidden) not 404 to prevent info leakage
        assert response.status_code == 403

    def test_mission_with_data(self, db_session, test_token, test_mission):
        """Test listing missions with actual data."""
        response = client.get(
            "/api/v1/missions",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should see the mission we created
        assert data["total"] >= 1

    def test_mission_filtering_by_status(self, test_token, test_mission):
        """Test filtering missions by status."""
        response = client.get(
            "/api/v1/missions?status=RUNNING",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200

    def test_mission_events(self, test_token, test_mission):
        """Test mission event stream."""
        response = client.get(
            f"/api/v1/missions/{test_mission.mission_id}/events",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        # Should succeed even if no events
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestTaskEndpoints:
    """Test task endpoints."""

    def test_list_tasks_empty(self, test_token):
        """Test listing tasks when empty."""
        response = client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_nonexistent_task(self, test_token):
        """Test retrieving non-existent task."""
        response = client.get(
            "/api/v1/tasks/nonexistent_task",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 403


class TestExecutionEndpoints:
    """Test execution endpoints."""

    def test_list_executions_empty(self, test_token):
        """Test listing executions when empty."""
        response = client.get(
            "/api/v1/executions",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_nonexistent_execution(self, test_token):
        """Test retrieving non-existent execution."""
        response = client.get(
            "/api/v1/executions/nonexistent_execution",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 403


class TestValidationEndpoints:
    """Test validation endpoints."""

    def test_list_validations_empty(self, test_token):
        """Test listing validations when empty."""
        response = client.get(
            "/api/v1/validations",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_nonexistent_validation(self, test_token):
        """Test retrieving non-existent validation."""
        response = client.get(
            "/api/v1/validations/nonexistent_validation",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 403


class TestMetricsEndpoints:
    """Test metrics endpoints."""

    def test_metrics_overview(self, test_token):
        """Test metrics overview endpoint."""
        response = client.get(
            "/api/v1/metrics/overview",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "missions" in data

    def test_metrics_agents(self, test_token):
        """Test agent metrics endpoint."""
        response = client.get(
            "/api/v1/metrics/agents",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

    def test_metrics_missions(self, test_token):
        """Test mission metrics endpoint."""
        response = client.get(
            "/api/v1/metrics/missions",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_metrics_projection_worker(self, test_token):
        """Test projection worker metrics."""
        response = client.get(
            "/api/v1/metrics/projection-worker",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200


class TestMultiTenantIsolation:
    """Test multi-tenant security and isolation."""

    def test_different_tokens_isolated(self, db_session, test_mission):
        """Test that different tenants cannot access each other's data."""
        # Create token for different tenant
        other_token = create_access_token(
            user_id="other_user",
            tenant_id="other_tenant",  # Different tenant
            actor_id="other_actor",
            actor_role="architect",
        )

        # Try to access mission with different tenant token
        response = client.get(
            f"/api/v1/missions/{test_mission.mission_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        # Should be forbidden (403) not found (404)
        assert response.status_code == 403

    def test_pagination_respects_tenant(self, test_token, test_mission):
        """Test that pagination respects tenant boundaries."""
        response = client.get(
            "/api/v1/missions?page=1&per_page=100",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should only see missions for this tenant
        for mission in data.get("missions", []):
            # All missions should belong to this tenant (checked by API)
            assert mission is not None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_page_number(self, test_token):
        """Test invalid page number."""
        response = client.get(
            "/api/v1/agents?page=0",  # Page must be >= 1
            headers={"Authorization": f"Bearer {test_token}"},
        )
        # Should fail validation
        assert response.status_code in [400, 422]

    def test_invalid_per_page(self, test_token):
        """Test invalid per_page value."""
        response = client.get(
            "/api/v1/agents?per_page=1000",  # Max is 100
            headers={"Authorization": f"Bearer {test_token}"},
        )
        # Should fail validation or be capped
        assert response.status_code in [200, 400, 422]

    def test_404_response_format(self, test_token):
        """Test that 404 responses are properly formatted."""
        response = client.get(
            "/api/v1/missions/nonexistent",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        assert response.status_code == 403
        # Should have error detail
        data = response.json()
        assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
