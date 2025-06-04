"""
Tests for the OpenPypi API authentication endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from openpypi.api.app import app  # Main FastAPI app
from openpypi.core.config import Config
from openpypi.core.security import UserInDB, get_password_hash  # For mocking user data


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture(scope="module")
def test_user_credentials():
    return {"username": "authtestuser", "password": "authtestpassword"}


@pytest.fixture(scope="module")
def mock_config_with_api_keys(test_user_credentials):
    """Fixture to provide a Config instance with API keys for testing get_api_key."""
    # Simulate a UserInDB for fake_users_db used by auth routes
    hashed_password = get_password_hash(test_user_credentials["password"])
    user_in_db = UserInDB(
        username=test_user_credentials["username"],
        email=f"{test_user_credentials['username']}@example.com",
        full_name="Auth Test User",
        hashed_password=hashed_password,
        disabled=False,
    )
    # This key is used by get_api_key via dependencies.py
    # The actual token for /auth/token is JWT, API key is for other endpoints generally.
    return Config(
        api_keys=["test_api_key_123"],
        fake_users_db_override={test_user_credentials["username"]: user_in_db},
    )


def test_login_for_access_token(
    client: TestClient, test_user_credentials, mock_config_with_api_keys
):
    """Test successful login and token generation."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    # Override the dependency
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config

    app.dependency_overrides[get_config] = override_get_config

    try:
        response = client.post("/api/v1/auth/token", data=test_user_credentials)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_login_for_access_token_invalid_credentials(client: TestClient, mock_config_with_api_keys):
    """Test login with invalid credentials."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    # Override the dependency
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config

    app.dependency_overrides[get_config] = override_get_config

    try:
        response = client.post(
            "/api/v1/auth/token", data={"username": "wronguser", "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Incorrect username or password"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_register_user_success(client: TestClient, mock_config_with_api_keys):
    """Test successful user registration."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    # Override the dependency
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config

    app.dependency_overrides[get_config] = override_get_config

    try:
        new_user_data = {
            "username": "newtestuser",
            "password": "newpassword123",
            "email": "new@example.com",
            "full_name": "New Test User",
        }
        response = client.post("/api/v1/auth/register", json=new_user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == new_user_data["username"]
        assert "email" in data
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_register_user_already_exists(
    client: TestClient, test_user_credentials, mock_config_with_api_keys
):
    """Test registration of an already existing user."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    # Override the dependency
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config

    app.dependency_overrides[get_config] = override_get_config

    try:
        user_data = {
            "username": test_user_credentials["username"],
            "password": test_user_credentials["password"],
            "email": "existing@example.com",
            "full_name": "Existing User",
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Username already registered"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_read_users_me(client: TestClient, test_user_credentials, mock_config_with_api_keys):
    """Test retrieving current user information with a valid API key."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    def override_get_current_user():
        return {"api_key": "test_api_key_123", "username": test_user_credentials["username"]}

    # Override the dependencies
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config, get_current_user

    app.dependency_overrides[get_config] = override_get_config
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.get("/api/v1/auth/users/me", headers={"X-API-Key": "test_api_key_123"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == test_user_credentials["username"]
        assert "email" in data
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_read_users_me_invalid_key(client: TestClient, mock_config_with_api_keys):
    """Test retrieving current user with an invalid API key."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    # Override the dependency
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config

    app.dependency_overrides[get_config] = override_get_config

    try:
        response = client.get("/api/v1/auth/users/me", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid API Key"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_validate_token_success(client: TestClient, mock_config_with_api_keys):
    """Test /validate-token endpoint with a valid API key."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    def override_get_current_user():
        return {"api_key": "test_api_key_123", "username": "mocked_user_for_valid_token"}

    # Override the dependencies
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config, get_current_user

    app.dependency_overrides[get_config] = override_get_config
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.get("/api/v1/auth/validate-token", headers={"X-API-Key": "test_api_key_123"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Token is valid."
        assert data["data"]["username"] == "mocked_user_for_valid_token"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_validate_token_failure(client: TestClient, mock_config_with_api_keys):
    """Test /validate-token endpoint with an invalid API key."""

    # Use FastAPI dependency override instead of mocking
    def override_get_config():
        return mock_config_with_api_keys

    # Override the dependency
    from openpypi.api.app import app
    from openpypi.api.dependencies import get_config

    app.dependency_overrides[get_config] = override_get_config

    try:
        response = client.get("/api/v1/auth/validate-token", headers={"X-API-Key": "invalid_api_key"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid API Key"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()
