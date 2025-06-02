"""
Base stage class for all pipeline stages.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from openpypi.core.context import PackageContext
from openpypi.providers.base import BaseProvider
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class BaseStage(ABC):
    """
    Abstract base class for all pipeline stages.
    
    Each stage implements a specific part of the package creation process
    and follows a consistent interface for execution and validation.
    """
    
    def __init__(self, provider: BaseProvider):
        """
        Initialize the stage with an AI provider.
        
        Args:
            provider: AI provider instance
        """
        self.provider = provider
        self.stage_name = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, context: PackageContext) -> None:
        """
        Execute the stage logic.
        
        Args:
            context: Package context containing all stage data
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this stage."""
        pass
    
    @abstractmethod
    def get_user_prompt(self, context: PackageContext) -> str:
        """
        Get the user prompt for this stage.
        
        Args:
            context: Package context
            
        Returns:
            Formatted user prompt
        """
        pass
    
    async def validate_output(self, output: Dict[str, Any]) -> bool:
        """
        Validate the stage output.
        
        Args:
            output: Stage output to validate
            
        Returns:
            True if output is valid, False otherwise
        """
        return True  # Default implementation
    
    def log_stage_start(self) -> None:
        """Log stage start."""
        logger.info(f"Starting {self.stage_name}")
    
    def log_stage_end(self) -> None:
        """Log stage completion."""
        logger.info(f"Completed {self.stage_name}")
    
    def log_stage_error(self, error: Exception) -> None:
        """Log stage error."""
        logger.error(f"Error in {self.stage_name}: {str(error)}")