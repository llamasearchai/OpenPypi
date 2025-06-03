"""
Comprehensive tests for health API endpoints.
"""

import time
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from openpypi.api.app import app

client = TestClient(app)


class TestHealthEndpointsComprehensive:
    """Comprehensive health endpoint tests."""

    def test_health_check_basic(self):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_check_detailed(self):
        """Test detailed health check endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()

        # Check required fields based on actual API response
        required_fields = ["status", "timestamp", "dependencies"]
        for field in required_fields:
            assert field in data

        # Check that dependencies contains expected services
        assert "dependencies" in data
        dependencies = data["dependencies"]
        expected_services = ["api", "database", "filesystem", "openai_api"]
        for service in expected_services:
            assert service in dependencies

    def test_health_check_performance(self):
        """Test health check response time."""
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 1.0  # Should respond within 1 second
        assert response.status_code == 200

    def test_health_check_concurrent_requests(self):
        """Test health endpoint under concurrent load."""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [future.result() for future in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    @patch("openpypi.api.dependencies.get_openai_client")
    def test_health_with_openai_dependency(self, mock_openai):
        """Test health check with OpenAI dependency."""
        mock_client = Mock()
        mock_openai.return_value = mock_client

        response = client.get("/health/detailed")
        assert response.status_code == 200

    def test_readiness_probe(self):
        """Test Kubernetes readiness probe endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200

    def test_liveness_probe(self):
        """Test Kubernetes liveness probe endpoint."""
        response = client.get("/live")
        assert response.status_code == 200
