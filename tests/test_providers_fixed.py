"""
Fixed provider tests with comprehensive mocking.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from openpypi.core.exceptions import ProviderError
from openpypi.providers.openai_provider import OpenAIProvider


class TestOpenAIProviderFixed:
    """Fixed OpenAI provider tests."""

    def test_initialization_with_config(self, mock_env_vars):
        """Test provider initialization with configuration."""
        config = {"api_key": "test-key"}
        with patch("openpypi.providers.openai_provider.OpenAI") as mock_openai:
            # Mock the validation call
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(config)
            assert provider.name == "openai"
            assert provider.config == config

    @patch("openpypi.providers.openai_provider.OpenAI")
    def test_generate_code_success(self, mock_openai, mock_env_vars):
        """Test successful code generation."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"main_code": "print(\\"Hello World\\")"}'
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.total_tokens = 150

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = OpenAIProvider({"api_key": "test-key"})

        # Test synchronous method
        result = provider.review_code("def hello(): print('world')")

        assert "review" in result
        assert result["score"] == "N/A"
        # Should be called twice: once for validation, once for review
        assert mock_client.chat.completions.create.call_count == 2

    def test_get_capabilities(self, mock_env_vars):
        """Test getting provider capabilities."""
        with patch("openpypi.providers.openai_provider.OpenAI") as mock_openai:
            # Mock the validation call
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIProvider({"api_key": "test-key"})
            capabilities = provider.get_capabilities()
            expected = ["code_generation", "code_review", "documentation_generation"]
            assert capabilities == expected

    def test_missing_api_key(self, mock_env_vars):
        """Test error handling for missing API key."""
        # Clear the mock environment variable
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ProviderError, match="OpenAI API key not configured"):
                OpenAIProvider({})
