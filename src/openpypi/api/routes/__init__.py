"""
API Routes for OpenPypi.

This package contains all the API route definitions, organized by functionality.
"""

from . import auth, generation, health, openai_integration, projects

__all__ = ["auth", "generation", "health", "openai_integration", "projects"]
