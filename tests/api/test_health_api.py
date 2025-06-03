"""
Tests for the OpenPypi API health check endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch  # Added AsyncMock

import pytest
from fastapi.testclient import TestClient

# Assuming your FastAPI app instance is accessible for testing
# If your app creation is complex, you might need a fixture to provide the client
from openpypi.api.app import app  # Adjust import if your app instance is elsewhere


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Test client for the FastAPI application."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_health_success(client: TestClient):
    """Test the /health endpoint for a successful response."""
    mock_openai_client = MagicMock()
    mock_openai_client.models.list = MagicMock(return_value=MagicMock(data=[]))

    # Use FastAPI dependency override instead of patching
    def override_get_openai_client():
        return mock_openai_client

    def override_get_db():
        return None

    from openpypi.api.app import app
    from openpypi.api.dependencies import get_db, get_openai_client

    app.dependency_overrides[get_openai_client] = override_get_openai_client
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "dependencies" in data
        assert data["dependencies"]["database"] == "not_checked"
        assert data["dependencies"]["openai_api"] == "healthy"
        assert "uptime_seconds" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_health_openai_failure(client: TestClient):
    """Test /health when OpenAI dependency check fails."""
    mock_openai_client = MagicMock()
    mock_openai_client.models.list = MagicMock(side_effect=Exception("OpenAI Connection Error"))

    # Use FastAPI dependency override instead of patching
    def override_get_openai_client():
        return mock_openai_client

    def override_get_db():
        return None

    from openpypi.api.app import app
    from openpypi.api.dependencies import get_db, get_openai_client

    app.dependency_overrides[get_openai_client] = override_get_openai_client
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["dependencies"]["openai_api"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_health_openai_not_configured(client: TestClient):
    """Test /health when OpenAI is not configured."""

    # Use FastAPI dependency override instead of patching
    def override_get_openai_client():
        return None

    from openpypi.api.app import app
    from openpypi.api.dependencies import get_openai_client

    app.dependency_overrides[get_openai_client] = override_get_openai_client

    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"]["openai_api"] == "not_configured"
        assert data["status"] == "healthy"
    finally:
        app.dependency_overrides.clear()


def test_ping_endpoint(client: TestClient):
    """Test the /health/ping endpoint."""
    response = client.get("/health/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "pong"
