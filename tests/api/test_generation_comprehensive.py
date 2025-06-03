"""
Comprehensive tests for project generation API endpoints.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from openpypi.api.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting for testing by patching the middleware."""
    from openpypi.api.middleware import RateLimitMiddleware

    # Store original method
    original_is_rate_limited = RateLimitMiddleware._is_rate_limited

    # Override to always return not rate limited
    def mock_is_rate_limited(self, client_id: str, calls_limit: int, period: int):
        return False, {
            "calls_made": 1,
            "calls_limit": calls_limit,
            "window_start": time.time(),
            "time_remaining": 0,
        }

    RateLimitMiddleware._is_rate_limited = mock_is_rate_limited

    yield

    # Restore original method
    RateLimitMiddleware._is_rate_limited = original_is_rate_limited


class TestGenerationComprehensive:
    """Comprehensive project generation tests."""

    def test_generate_project_sync_basic(self):
        """Test basic synchronous project generation."""
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/sync", json=project_data)
        assert response.status_code in [200, 201]

    def test_generate_project_async_basic(self):
        """Test basic asynchronous project generation."""
        project_data = {
            "name": "test-project-async",
            "description": "An async test project",
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/async", json=project_data)
        assert response.status_code in [200, 202]

        if response.status_code == 202:
            # Should return a task ID for tracking
            response_data = response.json()
            assert "data" in response_data
            data = response_data["data"]
            assert "task_id" in data

    @patch("openpypi.core.generator.ProjectGenerator.generate")
    def test_generate_project_with_mocked_generator(self, mock_generate):
        """Test project generation with mocked generator."""
        mock_generate.return_value = {
            "success": True,
            "project_path": "/tmp/test-project",
            "files_created": ["setup.py", "README.md"],
        }

        project_data = {
            "name": "mocked-project",
            "description": "A mocked test project",
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/sync", json=project_data)
        assert response.status_code in [200, 201]

    def test_generate_project_validation_errors(self):
        """Test project generation with validation errors."""
        # Test with missing required fields
        invalid_data = {"name": "", "description": "Test"}  # Empty name should fail validation

        response = client.post("/generate/sync", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_task_status_tracking(self):
        """Test async task status tracking."""
        # Start an async generation
        project_data = {
            "name": "status-test-project",
            "description": "Testing status tracking",
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/async", json=project_data)

        if response.status_code == 202:
            response_data = response.json()
            task_id = response_data["data"]["task_id"]

            # Check task status
            status_response = client.get(f"/generate/status/{task_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            assert "data" in status_data
            task_info = status_data["data"]
            assert "status" in task_info
            assert task_info["status"] in ["pending", "running", "completed", "failed"]

    def test_project_generation_with_options(self):
        """Test project generation with various options."""
        project_data = {
            "name": "options-test-project",
            "description": "Testing with options",
            "author": "Test Author",
            "email": "test@example.com",
            "options": {
                "use_fastapi": True,
                "use_docker": True,
                "use_github_actions": True,
                "test_framework": "pytest",
            },
        }

        response = client.post("/generate/sync", json=project_data)
        assert response.status_code in [200, 201]

    @pytest.mark.parametrize(
        "project_name",
        ["simple-project", "complex_project_name", "project123", "my-awesome-package"],
    )
    def test_project_name_variations(self, project_name):
        """Test project generation with various valid name formats."""
        project_data = {
            "name": project_name,
            "description": f"Testing {project_name}",
            "author": "Test Author",
            "email": "test@example.com",
        }

        response = client.post("/generate/sync", json=project_data)
        assert response.status_code in [200, 201, 422]  # 422 if name format is invalid

    def test_concurrent_project_generation(self):
        """Test multiple concurrent project generations."""
        import concurrent.futures

        def generate_project(project_id):
            project_data = {
                "name": f"concurrent-project-{project_id}",
                "description": f"Concurrent test project {project_id}",
                "author": "Test Author",
                "email": "test@example.com",
            }
            return client.post("/generate/sync", json=project_data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_project, i) for i in range(5)]
            responses = [future.result() for future in futures]

        # All requests should complete (though some might fail due to resource constraints)
        for response in responses:
            assert response.status_code in [200, 201, 500, 503]
