"""
OpenAI provider implementation with full API integration.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union

import openai
from openai import AsyncOpenAI, OpenAI
from pydantic import SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random_exponential

from ..core.exceptions import ProviderError
from ..utils.logger import get_logger
from .base import AIBaseProvider

logger = get_logger(__name__)


class OpenAIProvider(AIBaseProvider):
    """
    OpenAI provider with comprehensive API integration.

    Supports GPT-4, GPT-3.5-turbo, and other OpenAI models with
    advanced features like function calling, streaming, and
    sophisticated prompt engineering.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize OpenAI provider.

        Args:
            config: Configuration dictionary
        """
        # Store config first
        self.config = config or {}

        # Try to get API key first (this may raise ProviderError)
        try:
            self.api_key = self._get_secure_api_key()
            self.client = OpenAI(api_key=self.api_key.get_secret_value())
            self.client_initialized = True
        except ProviderError:
            self.client = None
            self.client_initialized = False
            # Re-raise the error to fail fast
            raise

        # Initialize parent class after client setup
        super().__init__(config)

        # Model capabilities
        self.model_info = self._get_model_capabilities()

        logger.info(f"OpenAI provider initialized")

    def _get_secure_api_key(self) -> SecretStr:
        """Get API key securely from config or environment."""
        key = self.config.get("api_key") if self.config else os.getenv("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OpenAI API key not configured")
        return SecretStr(key)

    def _get_model_capabilities(self) -> Dict[str, Any]:
        """Get model capabilities and limits."""
        capabilities = {
            "gpt-4-turbo-preview": {
                "max_tokens": 128000,
                "supports_functions": True,
                "supports_vision": False,
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03,
            },
            "gpt-4": {
                "max_tokens": 8192,
                "supports_functions": True,
                "supports_vision": False,
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06,
            },
            "gpt-3.5-turbo": {
                "max_tokens": 16385,
                "supports_functions": True,
                "supports_vision": False,
                "cost_per_1k_input": 0.0015,
                "cost_per_1k_output": 0.002,
            },
        }

        return capabilities.get(self.model, capabilities["gpt-3.5-turbo"])

    def get_capabilities(self) -> List[str]:
        """Get provider capabilities."""
        return ["code_generation", "code_review", "documentation_generation"]

    def validate_connection(self) -> bool:
        """Validate OpenAI API connection."""
        if not self.client_initialized or not self.client:
            return False

        try:
            # Make a simple API call to test connection
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": "test"}], max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate response from OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            functions: Function definitions for function calling
            function_call: Function call specification
            **kwargs: Additional parameters

        Returns:
            Response dictionary with content and metadata
        """
        try:
            # Prepare messages
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }

            # Add function calling if supported and provided
            if functions and self.model_info.get("supports_functions", False):
                request_params["functions"] = functions
                if function_call:
                    request_params["function_call"] = function_call

            # Make API call
            start_time = time.time()
            response = self.client.chat.completions.create(**request_params)
            end_time = time.time()

            # Extract response data
            message = response.choices[0].message

            result = {
                "content": message.content,
                "function_call": (
                    message.function_call.model_dump() if message.function_call else None
                ),
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "model": response.model,
                "response_time": end_time - start_time,
            }

            logger.debug(f"OpenAI API call completed in {result['response_time']:.2f}s")
            logger.debug(f"Token usage: {result['usage']}")

            return result

        except openai.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            await asyncio.sleep(60)  # Wait 1 minute
            raise

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=4, max=60),
        retry_error_callback=lambda _: None,
    )
    async def generate_code(
        self,
        specification: str,
        language: str = "python",
        style: str = "professional",
        include_tests: bool = True,
        include_docs: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate code using specialized prompts.

        Args:
            specification: Code specification
            language: Programming language
            style: Code style (professional, minimal, verbose)
            include_tests: Whether to include tests
            include_docs: Whether to include documentation
            **kwargs: Additional parameters

        Returns:
            Generated code and metadata
        """
        system_prompt = f"""You are an expert {language} developer. Generate high-quality, 
        production-ready code that follows best practices, includes proper error handling, 
        type hints, and comprehensive documentation.
        
        Style: {style}
        Include tests: {include_tests}
        Include documentation: {include_docs}
        
        Ensure the code is:
        - Well-structured and modular
        - Follows PEP 8 (for Python)
        - Includes proper error handling
        - Has comprehensive type hints
        - Is thoroughly documented
        - Includes examples where appropriate
        """

        prompt = f"""Generate {language} code for the following specification:

        {specification}

        Please provide:
        1. Main implementation code
        2. Test code (if requested)
        3. Documentation/docstrings
        4. Usage examples
        5. Dependencies list

        Format the response as JSON with the following structure:
        {{
            "main_code": "...",
            "test_code": "...",
            "documentation": "...",
            "examples": "...",
            "dependencies": ["..."],
            "explanation": "..."
        }}
        """

        response = await self.generate_response(prompt, system_prompt)

        try:
            # Try to parse JSON response
            code_data = json.loads(response["content"])
            return {
                "success": True,
                "code_data": code_data,
                "metadata": {
                    "tokens_used": response["usage"]["total_tokens"],
                    "response_time": response["response_time"],
                },
            }
        except json.JSONDecodeError:
            # Fallback to plain text response
            return {
                "success": False,
                "raw_content": response["content"],
                "metadata": {
                    "tokens_used": response["usage"]["total_tokens"],
                    "response_time": response["response_time"],
                },
            }

    async def estimate_cost(self, text: str) -> Dict[str, float]:
        """
        Estimate the cost of processing given text.

        Args:
            text: Text to estimate cost for

        Returns:
            Cost estimation dictionary
        """
        # Rough token estimation (1 token ≈ 4 characters)
        estimated_tokens = len(text) // 4

        input_cost = (estimated_tokens / 1000) * self.model_info["cost_per_1k_input"]

        # Estimate output tokens (usually 20-50% of input)
        estimated_output_tokens = estimated_tokens * 0.3
        output_cost = (estimated_output_tokens / 1000) * self.model_info["cost_per_1k_output"]

        total_cost = input_cost + output_cost

        return {
            "estimated_input_tokens": estimated_tokens,
            "estimated_output_tokens": int(estimated_output_tokens),
            "estimated_total_tokens": int(estimated_tokens + estimated_output_tokens),
            "estimated_input_cost": input_cost,
            "estimated_output_cost": output_cost,
            "estimated_total_cost": total_cost,
        }

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model": self.model,
            "provider": "openai",
            "capabilities": self.model_info,
            "configuration": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timeout": self.timeout,
            },
        }

    def review_code(self, code: str) -> Dict[str, str]:
        """Review code using OpenAI (synchronous method for backward compatibility)."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant that reviews Python code.",
                    },
                    {
                        "role": "user",
                        "content": f"Review this code for quality, style and potential issues:\n\n{code}",
                    },
                ],
                temperature=0.5,
                max_tokens=2000,
            )
            return {
                "review": response.choices[0].message.content,
                "score": "N/A",  # Could parse this from response
            }
        except Exception as e:
            raise ProviderError(f"OpenAI review failed: {e}") from e
