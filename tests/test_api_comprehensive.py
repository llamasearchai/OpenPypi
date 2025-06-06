"""Comprehensive API tests to boost coverage."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from openpypi.api.app import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test all API endpoints comprehensively."""

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_generate_endpoint_success(self):
        """Test successful project generation."""
        with patch("openpypi.core.ProjectGenerator") as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_project_structure.return_value = {
                "success": True,
                "files_created": ["setup.py", "README.md"],
                "directories_created": ["src/", "tests/"],
            }
            mock_generator.return_value = mock_instance

            payload = {
                "project_name": "test_project",
                "package_name": "test_package",
                "author": "Test Author",
                "email": "test@example.com",
                "description": "A test package",
                "use_fastapi": True,
                "use_openai": True,
            }

            response = client.post("/generate", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_generate_endpoint_validation_error(self):
        """Test generation with validation errors."""
        payload = {
            "project_name": "",  # Invalid empty name
            "package_name": "test_package",
            "author": "Test Author",
            "email": "invalid-email",  # Invalid email
        }

        response = client.post("/generate", json=payload)
        assert response.status_code == 422  # Validation error

    def test_templates_endpoint(self):
        """Test templates listing endpoint."""
        response = client.get("/templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_stages_endpoint(self):
        """Test stages listing endpoint."""
        response = client.get("/stages")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_providers_endpoint(self):
        """Test providers listing endpoint."""
        response = client.get("/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
