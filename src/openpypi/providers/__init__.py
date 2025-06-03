"""
Provider management system for OpenPypi.
"""

import importlib
from typing import Any, Dict, List, Optional, Type, Generic, TypeVar

from ..utils.logger import get_logger
from .base import BaseProvider, AIBaseProvider
from .ai import AIProvider, OpenAIProvider
from .github import GitHubProvider
from .docker import DockerProvider
from .cloud import CloudProvider
from .database import DatabaseProvider

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseProvider)

class ProviderRegistry(Generic[T]):
    """Type-safe provider registry with dependency management"""
    
    def __init__(self):
        self._providers: Dict[str, Type[T]] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._instances: Dict[str, T] = {}
        self._ai_providers = {}
        self._initialize_core_providers()
    
    def _initialize_core_providers(self):
        """Register core providers."""
        self.register("ai", AIProvider)
        self.register("openai", OpenAIProvider)
        self.register("github", GitHubProvider)
        self.register("docker", DockerProvider)
        self.register("cloud", CloudProvider)
        self.register("database", DatabaseProvider)
    
    def register(
        self, 
        name: str, 
        provider: Type[T],
        dependencies: Optional[List[str]] = None
    ):
        """Register provider with dependency checks"""
        if not issubclass(provider, BaseProvider):
            raise TypeError(f"{provider.__name__} must inherit from BaseProvider")
            
        missing_deps = [dep for dep in (dependencies or []) if dep not in self._providers]
        if missing_deps:
            raise ValueError(f"Missing dependencies: {missing_deps}")
            
        self._providers[name] = provider
        self._dependencies[name] = dependencies or []
        
        if issubclass(provider, AIBaseProvider):
            self._ai_providers[name] = provider
    
    def unregister_provider(self, name: str) -> None:
        """Unregister a provider."""
        if name in self._providers:
            del self._providers[name]
            if name in self._instances:
                del self._instances[name]
            logger.info(f"Unregistered provider: {name}")
    
    def get_provider(self, name: str, config: dict = None) -> T:
        """Get provider instance with dependency resolution"""
        if name not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Provider '{name}' not found. Available: {available}")
            
        if name in self._instances:
            return self._instances[name]
            
        # Resolve dependencies first
        for dep in self._dependencies.get(name, []):
            self.get_provider(dep, config)
            
        instance = self._providers[name](config or {})
        self._instances[name] = instance
        return instance
    
    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self._providers.keys())
    
    def list_ai_providers(self) -> List[str]:
        """List all AI providers."""
        return list(self._ai_providers.keys())
    
    def get_provider_info(self, name: str) -> Dict[str, Any]:
        """Get information about a provider."""
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' not found")
        
        provider_class = self._providers[name]
        
        # Try to get capabilities from the class
        capabilities = []
        try:
            # Create temporary instance to get capabilities
            temp_instance = provider_class({})
            if hasattr(temp_instance, 'get_capabilities'):
                capabilities = temp_instance.get_capabilities()
        except Exception as e:
            logger.debug(f"Could not get capabilities for {name}: {e}")
        
        return {
            "name": name,
            "class": provider_class.__name__,
            "module": provider_class.__module__,
            "capabilities": capabilities,
            "description": provider_class.__doc__ or "No description available"
        }
    
    def clear_cache(self) -> None:
        """Clear the provider instance cache."""
        self._instances.clear()
        logger.debug("Provider cache cleared")
    
    @property 
    def providers(self) -> Dict[str, Type]:
        """Get the providers dictionary (for testing)."""
        return self._providers.copy()

    def validate_ecosystem(self) -> bool:
        """Validate all provider dependencies are satisfied"""
        return all(
            all(dep in self._providers for dep in deps)
            for deps in self._dependencies.values()
        )


class ProviderNotFoundError(Exception):
    """Raised when a provider is not found."""
    pass


# Global registry instance
_registry = ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    return _registry


def register_provider(name: str, provider_class: Type) -> None:
    """Register a provider globally."""
    _registry.register(name, provider_class)


def get_provider(name: str, config: Optional[Dict[str, Any]] = None) -> Any:
    """Get a provider instance globally."""
    return _registry.get_provider(name, config)


def list_providers() -> List[str]:
    """List all registered providers globally."""
    return _registry.list_providers()


# Make registry available for import
registry = _registry

# Import provider classes for external use
try:
    from .base import BaseProvider as Provider
    from .ai import AIProvider
    from .openai_provider import OpenAIProvider
    from .cloud import CloudProvider
    from .database import DatabaseProvider
    from .docker import DockerProvider
    from .github import GitHubProvider
except ImportError as e:
    logger.debug(f"Error importing provider classes: {e}")
    # Create dummy classes for missing providers
    Provider = type('Provider', (), {})
    AIProvider = type('AIProvider', (), {})
    OpenAIProvider = type('OpenAIProvider', (), {})
    CloudProvider = type('CloudProvider', (), {})
    DatabaseProvider = type('DatabaseProvider', (), {})
    DockerProvider = type('DockerProvider', (), {})
    GitHubProvider = type('GitHubProvider', (), {})

# Export main components
__all__ = [
    "ProviderRegistry",
    "ProviderNotFoundError",
    "get_provider_registry", 
    "register_provider",
    "get_provider",
    "list_providers",
    "registry",
    "Provider",
    "AIProvider",
    "OpenAIProvider", 
    "CloudProvider",
    "DatabaseProvider",
    "DockerProvider",
    "GitHubProvider"
]
