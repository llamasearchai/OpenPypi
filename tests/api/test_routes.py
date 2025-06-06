"""Tests for API routes."""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from openpypi.api.app import create_app
from openpypi.core.config import Config


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "name": "test-project",
        "description": "A test project",
        "author": "Test Author",
        "email": "test@example.com",
        "options": {"use_fastapi": True, "use_docker": False, "test_framework": "pytest"},
    }


class TestHealthRoutes:
    """Test health check routes."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_liveness_probe(self, client):
        """Test liveness probe."""
        response = client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, client):
        """Test readiness probe."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_detailed_health_check(self, client):
        """Test detailed health check."""
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "system" in data["checks"]
        assert "database" in data["checks"]


class TestGenerateRoutes:
    """Test project generation routes."""

    @patch("openpypi.core.generator.ProjectGenerator")
    def test_generate_sync_success(self, mock_generator_class, client, sample_project_data):
        """Test successful synchronous project generation."""
        mock_generator = Mock()
        mock_generator.generate.return_value = {
            "project_dir": "/tmp/test-project",
            "files_created": ["file1.py", "file2.py"],
            "directories_created": ["src/", "tests/"],
            "commands_run": ["git init"],
            "warnings": [],
        }
        mock_generator_class.return_value = mock_generator

        response = client.post("/generate/sync", json=sample_project_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["project_dir"] == "/tmp/test-project"
        assert len(data["files_created"]) == 2
        assert len(data["directories_created"]) == 2

    def test_generate_sync_missing_name(self, client):
        """Test synchronous generation with missing project name."""
        data = {
            "description": "A test project",
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/sync", json=data)

        assert response.status_code == 422  # Validation error

    def test_generate_sync_invalid_email(self, client):
        """Test synchronous generation with invalid email."""
        data = {"name": "test-project", "author": "Test Author", "email": "invalid-email"}

        response = client.post("/generate/sync", json=data)

        assert response.status_code == 422  # Validation error

    @patch("openpypi.core.generator.ProjectGenerator")
    def test_generate_sync_generation_error(
        self, mock_generator_class, client, sample_project_data
    ):
        """Test synchronous generation with generation error."""
        from openpypi.core.exceptions import GenerationError

        mock_generator = Mock()
        mock_generator.generate.side_effect = GenerationError("Generation failed")
        mock_generator_class.return_value = mock_generator

        response = client.post("/generate/sync", json=sample_project_data)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Generation failed"

    @patch("openpypi.api.routes.background_tasks")
    def test_generate_async_success(self, mock_background_tasks, client, sample_project_data):
        """Test successful asynchronous project generation."""
        response = client.post("/generate/async", json=sample_project_data)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "task_id" in data
        assert data["message"] == "Project generation started"

    def test_generate_async_missing_data(self, client):
        """Test asynchronous generation with missing data."""
        response = client.post("/generate/async", json={})

        assert response.status_code == 422

    @patch("openpypi.api.routes.task_status")
    def test_get_task_status_success(self, mock_task_status, client):
        """Test getting task status."""
        task_id = "test-task-123"
        mock_task_status.return_value = {
            "status": "completed",
            "result": {
                "project_dir": "/tmp/test-project",
                "files_created": ["file1.py"],
                "directories_created": ["src/"],
            },
        }

        response = client.get(f"/generate/status/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "result" in data

    @patch("openpypi.api.routes.task_status")
    def test_get_task_status_not_found(self, mock_task_status, client):
        """Test getting status for non-existent task."""
        task_id = "non-existent-task"
        mock_task_status.return_value = None

        response = client.get(f"/generate/status/{task_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch("openpypi.api.routes.task_status")
    def test_get_task_status_running(self, mock_task_status, client):
        """Test getting status for running task."""
        task_id = "running-task-123"
        mock_task_status.return_value = {
            "status": "running",
            "progress": 50,
            "message": "Generating files...",
        }

        response = client.get(f"/generate/status/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["message"] == "Generating files..."

    @patch("openpypi.api.routes.task_status")
    def test_get_task_status_failed(self, mock_task_status, client):
        """Test getting status for failed task."""
        task_id = "failed-task-123"
        mock_task_status.return_value = {
            "status": "failed",
            "error": "Generation failed: Invalid configuration",
        }

        response = client.get(f"/generate/status/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Generation failed: Invalid configuration"


class TestMonitoringRoutes:
    """Test monitoring and metrics routes."""

    def test_get_metrics(self, client):
        """Test getting application metrics."""
        response = client.get("/monitoring/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "application" in data
        assert "system" in data
        assert "timestamp" in data

    def test_get_system_metrics(self, client):
        """Test getting system metrics."""
        response = client.get("/monitoring/metrics/system")

        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "disk_usage" in data
        assert "timestamp" in data

    def test_get_application_metrics(self, client):
        """Test getting application metrics."""
        response = client.get("/monitoring/metrics/application")

        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data
        assert "requests_per_second" in data
        assert "average_response_time" in data
        assert "active_connections" in data


class TestConfigRoutes:
    """Test configuration routes."""

    def test_get_config_info(self, client):
        """Test getting configuration information."""
        response = client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "features" in data
        assert "supported_templates" in data

    def test_validate_config_valid(self, client):
        """Test validating valid configuration."""
        config_data = {
            "project_name": "valid-project",
            "author": "Test Author",
            "email": "test@example.com",
            "use_fastapi": True,
        }

        response = client.post("/config/validate", json=config_data)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "errors" not in data or len(data["errors"]) == 0

    def test_validate_config_invalid(self, client):
        """Test validating invalid configuration."""
        config_data = {
            "project_name": "",  # Invalid: empty name
            "email": "invalid-email",  # Invalid: no @
            "version": "invalid-version",  # Invalid: not X.Y.Z format
        }

        response = client.post("/config/validate", json=config_data)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "errors" in data
        assert len(data["errors"]) > 0


class TestWebSocketRoutes:
    """Test WebSocket routes."""

    def test_websocket_generation_status(self, client):
        """Test WebSocket connection for generation status."""
        with client.websocket_connect("/ws/generation/test-task-123") as websocket:
            # This would typically test real-time status updates
            # For now, just test connection
            data = websocket.receive_json()
            assert "status" in data


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self, client):
        """Test 404 error handling."""
        response = client.get("/non-existent-endpoint")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test 405 method not allowed."""
        response = client.put("/health")  # PUT not allowed on health endpoint

        assert response.status_code == 405

    def test_large_payload(self, client):
        """Test handling of large payloads."""
        large_data = {
            "name": "test-project",
            "description": "x" * 10000,  # Large description
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/sync", json=large_data)

        # Should handle large payloads gracefully
        assert response.status_code in [200, 413, 422]
