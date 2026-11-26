"""
Test CORS configuration and preflight requests.
Validates that frontend at http://localhost:5173 can reach API at http://localhost:8000.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_allows_localhost_5173(self, client):
        """
        Test that CORS allows requests from http://localhost:5173.
        This is the Vite dev server origin.
        """
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "POST",
                "access-control-request-headers": "content-type",
            },
        )

        assert response.status_code == 200, f"Preflight failed: {response.text}"
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "POST" in response.headers.get("access-control-allow-methods", "")

    def test_cors_allows_localhost_3000(self, client):
        """Test that CORS allows requests from http://localhost:3000."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "POST",
                "access-control-request-headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_credentials(self, client):
        """Test that CORS allows credentials (for auth tokens)."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "POST",
                "access-control-request-headers": "content-type",
            },
        )

        # allow_credentials=True should be set
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_cors_allows_all_methods(self, client):
        """Test that CORS allows common HTTP methods."""
        response = client.options(
            "/api/v1/health",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "GET",
                "access-control-request-headers": "content-type",
            },
        )

        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods

    def test_cors_allows_headers(self, client):
        """Test that CORS allows common headers."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "POST",
                "access-control-request-headers": "content-type,authorization",
            },
        )

        # Should echo back requested headers
        assert response.status_code == 200


class TestLoginWithCORS:
    """Test that login endpoint works with CORS headers."""

    def test_login_post_request_includes_cors_headers(self, client):
        """Test that POST to login endpoint includes proper CORS headers."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test123"},
            headers={"origin": "http://localhost:5173"},
        )

        # Should have CORS header in response (even if login fails)
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
