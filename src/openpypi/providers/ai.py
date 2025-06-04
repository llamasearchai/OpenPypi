"""
AI provider for OpenAI Agents SDK integration and advanced AI capabilities.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

try:
    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat import ChatCompletion
except ImportError:
    OpenAI = None
    AsyncOpenAI = None
    ChatCompletion = None

from .base import AIBaseProvider

logger = logging.getLogger(__name__)


class AIProvider(AIBaseProvider):
    """Provider for AI services and agent orchestration."""

    @property
    def name(self) -> str:
        return "ai"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)

    def _configure(self) -> None:
        """Configure AI provider."""
        self.api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.max_tokens = self.config.get("max_tokens", 2048)
        self.temperature = self.config.get("temperature", 0.7)

        if self.api_key and OpenAI:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            self.is_configured = True
        else:
            logger.warning("OpenAI API key not configured or openai package not installed")
            self.is_configured = False

    def validate_connection(self) -> bool:
        """Validate AI provider connection."""
        if not self.is_configured:
            return False

        try:
            # Simple test to validate connection
            response = self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": "test"}], max_tokens=5
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(f"AI provider connection validation failed: {e}")
            return False

    def get_capabilities(self) -> List[str]:
        """Return AI provider capabilities."""
        return [
            "text_generation",
            "code_generation",
            "code_review",
            "test_generation",
            "documentation_generation",
            "analysis",
        ]

    def generate_code(self, prompt: str, language: str = "python") -> str:
        """Generate code using AI."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        system_prompt = f"""You are an expert {language} developer. Generate clean, 
        production-ready code that follows best practices. Include proper error handling,
        type hints, docstrings, and comments where appropriate."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response.choices[0].message.content

    def review_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Review code for quality, security, and best practices."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        system_prompt = f"""You are a senior code reviewer. Analyze the provided {language} 
        code for:
        1. Code quality and best practices
        2. Security vulnerabilities
        3. Performance issues
        4. Maintainability concerns
        5. Testing coverage gaps
        
        Provide specific recommendations for improvement."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Review this code:\n\n{code}"},
            ],
            max_tokens=self.max_tokens,
            temperature=0.3,
        )

        review_content = response.choices[0].message.content

        return {
            "review": review_content,
            "recommendations": self._extract_recommendations(review_content),
            "severity": self._assess_severity(review_content),
        }

    def _extract_recommendations(self, content: str) -> List[str]:
        """Extract recommendations from review content."""
        # Simple extraction logic - could be enhanced with NLP
        lines = content.split("\n")
        recommendations = []

        for line in lines:
            line = line.strip()
            if any(
                keyword in line.lower()
                for keyword in ["recommend", "suggest", "should", "consider"]
            ):
                recommendations.append(line)

        return recommendations[:10]  # Limit to top 10

    def _assess_severity(self, content: str) -> str:
        """Assess severity level from review content."""
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ["critical", "severe", "major security"]):
            return "high"
        elif any(keyword in content_lower for keyword in ["moderate", "minor", "warning"]):
            return "medium"
        else:
            return "low"

    def generate_tests(self, code: str, framework: str = "pytest") -> str:
        """Generate unit tests for provided code."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        system_prompt = f"""You are a test automation expert. Generate comprehensive 
        {framework} unit tests for the provided code. Include:
        1. Happy path tests
        2. Edge case tests
        3. Error condition tests
        4. Mock external dependencies
        5. Proper test structure and naming"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate tests for this code:\n\n{code}"},
            ],
            max_tokens=self.max_tokens,
            temperature=0.4,
        )

        return response.choices[0].message.content

    def analyze_architecture(self, project_structure: str) -> Dict[str, Any]:
        """Analyze project architecture and suggest improvements."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        system_prompt = """You are a software architecture expert. Analyze the provided 
        project structure and suggest improvements for:
        1. Architectural patterns and principles
        2. Module organization and dependencies
        3. Scalability considerations
        4. Security architecture
        5. Performance optimizations
        6. Maintainability improvements"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Analyze this project structure:\n\n{project_structure}",
                },
            ],
            max_tokens=self.max_tokens,
            temperature=0.6,
        )

        analysis = response.choices[0].message.content

        return {
            "analysis": analysis,
            "recommendations": self._extract_recommendations(analysis),
            "priority": self._assess_priority(analysis),
        }

    def _assess_priority(self, content: str) -> str:
        """Assess priority level from analysis content."""
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ["urgent", "critical", "immediately"]):
            return "high"
        elif any(keyword in content_lower for keyword in ["soon", "important", "should"]):
            return "medium"
        else:
            return "low"

    async def generate_code_async(self, prompt: str, language: str = "python") -> str:
        """Generate code asynchronously."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        system_prompt = f"""You are an expert {language} developer. Generate clean, 
        production-ready code that follows best practices."""

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response.choices[0].message.content

    def create_agent_workflow(self, task_description: str) -> Dict[str, Any]:
        """Create an agent workflow for complex tasks."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        system_prompt = """You are an AI agent orchestration expert. Design a workflow 
        for the given task that breaks it down into:
        1. Sequential steps
        2. Required tools/capabilities
        3. Success criteria
        4. Error handling strategies
        5. Quality checkpoints
        
        Return a structured workflow plan."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a workflow for: {task_description}"},
            ],
            max_tokens=self.max_tokens,
            temperature=0.5,
        )

        workflow_content = response.choices[0].message.content

        return {
            "workflow": workflow_content,
            "steps": self._extract_workflow_steps(workflow_content),
            "tools_required": self._extract_tools_required(workflow_content),
        }

    def _extract_workflow_steps(self, content: str) -> List[str]:
        """Extract workflow steps from content."""
        # Simple extraction logic
        lines = content.split("\n")
        steps = []

        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                steps.append(line)

        return steps[:20]  # Limit to reasonable number

    def _extract_tools_required(self, content: str) -> List[str]:
        """Extract required tools from workflow content."""
        # Simple extraction logic
        content_lower = content.lower()
        common_tools = [
            "git",
            "docker",
            "kubernetes",
            "pytest",
            "black",
            "mypy",
            "github",
            "gitlab",
            "jenkins",
            "terraform",
            "ansible",
        ]

        tools_found = []
        for tool in common_tools:
            if tool in content_lower:
                tools_found.append(tool)

        return tools_found

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a response from the AI model."""
        if not self.is_configured:
            raise RuntimeError("AI provider not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs,
        )

        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": response.usage.dict() if response.usage else None,
        }

    async def estimate_cost(self, tokens: int) -> Dict[str, float]:
        """Estimate cost for operations."""
        # Simple cost estimation based on OpenAI pricing
        cost_per_1k_tokens = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
        }

        base_cost = cost_per_1k_tokens.get(self.model, 0.002)
        estimated_cost = (tokens / 1000) * base_cost

        return {
            "estimated_cost": estimated_cost,
            "currency": "USD",
            "model": self.model,
            "tokens": tokens,
        }

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the AI model."""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "provider": "openai",
            "capabilities": self.get_capabilities(),
        }


class OpenAIProvider(AIProvider):
    """OpenAI specific provider with enhanced capabilities."""

    @property
    def name(self) -> str:
        return "openai"

    def _configure(self) -> None:
        """Configure OpenAI provider with enhanced settings."""
        self.api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.model = self.config.get("model", "gpt-4")
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.7)

        if self.api_key and OpenAI:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            self.is_configured = True
        else:
            logger.warning("OpenAI API key not configured or openai package not installed")
            self.is_configured = False

    def get_capabilities(self) -> List[str]:
        """Return enhanced OpenAI provider capabilities."""
        return [
            "code_generation",
            "code_review",
            "test_generation",
            "documentation_generation",
            "architecture_analysis",
            "security_scanning",
            "performance_optimization",
            "agent_orchestration",
        ]
