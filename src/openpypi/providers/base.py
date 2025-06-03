"""
Base provider interface with comprehensive functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..core.exceptions import ProviderError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ProviderConfig(BaseModel):
    """Enhanced configuration model with security constraints"""
    model_config = ConfigDict(extra='forbid', frozen=True)
    
    name: Annotated[str, Field(min_length=3, max_length=50, pattern=r'^[a-z0-9_]+$')]
    enabled: bool = True
    timeout: Annotated[int, Field(gt=0, le=300)] = 30
    retry_attempts: Annotated[int, Field(ge=0, le=10)] = 3
    security: dict = Field(
        default_factory=lambda: {"encrypt_secrets": True, "audit_logging": False},
        description="Security configuration parameters"
    )


class BaseProvider(ABC):
    """Enhanced base provider with lifecycle hooks"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name."""
        pass

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.is_configured = False
        try:
            self._configure()
            self._post_configure()
        except Exception as e:
            logger.error(f"Provider initialization failed: {e}")
            self.is_configured = False

    def _post_configure(self):
        """Post-configuration validation hook"""
        try:
            if hasattr(self, 'validate_connection') and callable(getattr(self, 'validate_connection')):
                if not self.validate_connection():
                    logger.warning("Post-configuration connection validation failed")
        except Exception as e:
            logger.warning(f"Connection validation error: {e}")

    @abstractmethod
    def _configure(self) -> None:
        """Configure provider with given configuration."""
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate provider connection."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of provider capabilities."""
        pass

    def shutdown(self):
        """Clean up resources before provider destruction"""
        logger.info(f"Shutting down provider: {self.name}")
        self.is_configured = False


class AIBaseProvider(BaseProvider):
    """Base class for AI-powered providers."""
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response to a prompt."""
        pass

    @abstractmethod
    async def generate_code(self, requirements: str, **kwargs) -> Dict[str, Any]:
        """Generate code based on requirements."""
        pass

    @abstractmethod
    async def estimate_cost(self, tokens: int) -> Dict[str, float]:
        """Estimate cost for operations."""
        pass

    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the AI model."""
        pass
