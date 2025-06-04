"""
Enhanced provider tests with comprehensive security and performance testing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

# Import providers
from openpypi.providers import registry, GitHubProvider, DockerProvider
from openpypi.providers.base import BaseProvider

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openpypi.providers import ProviderRegistry


def test_provider_registration():
    test_registry = ProviderRegistry()

    # Test core providers
    assert "github" in test_registry.list_providers()
    assert "docker" in test_registry.list_providers()
    assert "ai" in test_registry.list_ai_providers()

    # Test provider initialization
    github = test_registry.get_provider("github", {"token": "test"})
    assert github.name == "github"
    assert isinstance(github, GitHubProvider)


def test_github_provider_lifecycle():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200

        provider = GitHubProvider({"token": "ghp_test", "username": "testuser"})

        assert provider.is_configured
        assert provider.validate_connection()
        assert "create_repository" in provider.get_capabilities()


def test_docker_provider_security():
    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_docker.return_value = mock_client

        provider = DockerProvider({"socket_url": "tcp://localhost:2375", "timeout": 10})

        assert provider.is_configured
        assert provider.validate_connection()
        assert "build_image" in provider.get_capabilities()


class TestProviderSecurity:
    @pytest.mark.parametrize(
        "provider,config",
        [
            ("github", {"token": "invalid"}),
            ("docker", {"socket_url": "invalid"}),
        ],
    )
    def test_invalid_configurations(self, provider, config):
        with pytest.raises(ValidationError):
            registry.get_provider(provider, config)

    @given(st.text(min_size=1))
    def test_github_token_encryption(self, token):
        provider = GitHubProvider({"token": token})
        assert provider.token != token
        assert len(provider.token) == 44  # Fernet token length

    def test_docker_image_quarantine(self):
        with patch.object(
            DockerProvider,
            "build_image",
            return_value={"image_id": "test", "tags": ["vulnerable"], "success": True},
        ):
            with patch.object(
                DockerProvider, "security_scan_image", return_value={"vulnerabilities_found": True}
            ):
                provider = DockerProvider()
                result = provider.build_image("Dockerfile")
                assert "quarantine" in result.get("image_id", "")


class TestProviderPerformance:
    @pytest.mark.benchmark
    def test_github_api_response_time(self):
        provider = GitHubProvider(valid_config)
        start = time.time()
        provider.validate_connection()
        assert time.time() - start < 2.0  # 2 second SLA

    @pytest.mark.stress
    def test_docker_high_concurrency(self):
        with ThreadPoolExecutor(50) as executor:
            futures = [
                executor.submit(DockerProvider().build_image, "Dockerfile") for _ in range(100)
            ]
            results = [f.result() for f in futures]
            assert all(r["success"] for r in results)
