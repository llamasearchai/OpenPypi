"""
Base provider interface for AI providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class BaseProvider(ABC):
    """
    Abstract base class for AI providers.
    
    This defines the interface that all AI providers must implement
    to work with the OpenPypi system.
    """
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the AI model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Response dictionary with content and metadata
        """
        pass
    
    @abstractmethod
    async def generate_code(
        self,
        specification: str,
        language: str = "python",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate code based on specification.
        
        Args:
            specification: Code specification
            language: Programming language
            **kwargs: Additional parameters
            
        Returns:
            Generated code and metadata
        """
        pass
    
    @abstractmethod
    async def estimate_cost(self, text: str) -> Dict[str, float]:
        """
        Estimate the cost of processing given text.
        
        Args:
            text: Text to estimate cost for
            
        Returns:
            Cost estimation dictionary
        """
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        pass