"""
API Routes module for OpenPypi
Exports all route handlers for the FastAPI application
"""

from .auth import router as auth_router
from .projects import router as projects_router
from .packages import router as packages_router
from .health import router as health_router
from .admin import router as admin_router
from .generation import router as generation_router
from .monitoring import router as monitoring_router
from .openai_integration import router as openai_router

__all__ = [
    "auth_router",
    "projects_router", 
    "packages_router",
    "health_router",
    "admin_router",
    "generation_router",
    "monitoring_router",
    "openai_router",
]
