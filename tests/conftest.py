"""Pytest configuration and fixtures."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from openpypi.core.config import Config
from openpypi.providers.openai_provider import OpenAIProvider

try:
    from openpypi.utils.mock_data import generate_mock_projects, generate_mock_users
except ImportError:
    # Fallback mock data generators
    def generate_mock_users(count=3):
        return [{"id": i, "username": f"user{i}", "email": f"user{i}@example.com"} for i in range(count)]
    
    def generate_mock_projects(count=5):
        return [{"id": i, "name": f"project{i}", "description": f"Test project {i}"} for i in range(count)]

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from openpypi.core import Config, ProjectGenerator


@pytest.fixture(scope="session")
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "OPENAI_API_KEY": "sk-test-key-12345",
        "PYPI_API_TOKEN": "pypi-test-token-12345",
        "SECRET_KEY": "test-secret-key",
        "DATABASE_URL": "sqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("openai.OpenAI") as mock_client:
        # Mock completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated code content"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 300
        mock_response.model = "gpt-3.5-turbo"

        mock_client.return_value.chat.completions.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def sample_config() -> Config:
    """Provide sample configuration for tests."""
    return Config(
        project_name="test-project",
        package_name="test_project",
        author="Test Author",
        email="test@example.com",
        use_openai=True,
        use_fastapi=True,
        use_docker=True,
    )


@pytest.fixture
def minimal_config() -> Config:
    """Provide minimal configuration for tests."""
    return Config(
        project_name="minimal_project",
        package_name="minimal_package",
        author="Test Author",
        email="test@example.com",
        description="A minimal test package",
        use_fastapi=False,
        use_openai=False,
        use_docker=False,
        create_tests=False,
    )


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def project_generator(sample_config: Config) -> ProjectGenerator:
    """Create a project generator instance."""
    return ProjectGenerator(sample_config)


@pytest.fixture
def sample_metadata() -> Dict[str, Any]:
    """Provide sample project metadata."""
    return {
        "author": "Test Author",
        "email": "test@example.com",
        "description": "A test package",
        "license": "MIT",
        "python_requires": ">=3.8",
        "dependencies": ["fastapi>=0.104.0", "openai>=1.0.0"],
        "python_versions": ["3.8", "3.9", "3.10", "3.11", "3.12"],
    }


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess calls."""
    import subprocess

    def mock_run(*args, **kwargs):
        # Mock successful subprocess calls
        class MockResult:
            def __init__(self):
                self.returncode = 0
                self.stdout = ""
                self.stderr = ""

        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_response():
    """Provide mock HTTP response."""
    return MockResponse({"result": "success"})


@pytest.fixture
def mock_openai_response():
    """Provide mock OpenAI API response."""
    return {
        "choices": [{"message": {"content": "This is a test response from OpenAI"}}],
        "model": "gpt-3.5-turbo",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.fixture
def mock_users():
    """Generate mock users for testing."""
    return generate_mock_users(3)


@pytest.fixture
def mock_projects():
    """Generate mock projects for testing."""
    return generate_mock_projects(5)


@pytest.fixture
def openai_provider(mock_env_vars, mock_openai_client):
    """OpenAI provider instance for testing."""
    config = {"api_key": "sk-test-key-12345"}
    return OpenAIProvider(config)
