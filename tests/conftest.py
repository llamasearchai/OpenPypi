"""Pytest configuration and fixtures."""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from openpypi.core import Config, ProjectGenerator


@pytest.fixture
def sample_config() -> Config:
    """Provide sample configuration for tests."""
    return Config(
        project_name="test_project",
        package_name="test_package",
        author="Test Author",
        email="test@example.com",
        description="A test package",
        use_fastapi=True,
        use_openai=True,
        use_docker=True,
        create_tests=True,
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
