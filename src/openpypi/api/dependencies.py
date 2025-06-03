"""
FastAPI dependencies for OpenPypi API.
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from openai import OpenAI

from openpypi.core.config import Config
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)

# API Key Authentication
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_config() -> Config:
    """Dependency to get application configuration."""
    # In a real application, this might be loaded from a global state or context
    return Config()


async def get_api_key(
    api_key: str = Depends(api_key_header), config: Config = Depends(get_config)
) -> str:
    """Dependency to validate API key."""
    if not config.api_keys:
        logger.warning("No API keys configured. Allowing access by default.")
        # If no API keys are configured, allow access (consider security implications)
        # Or, raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API key security not configured")
        return "development_key"  # Placeholder for development

    if api_key in config.api_keys:
        return api_key
    else:
        logger.warning(f"Invalid API Key received: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )


def get_db() -> Generator:
    """Dependency for database session (placeholder)."""
    # Replace with actual database session management
    db = None
    try:
        # Example: db = SessionLocal()
        logger.info("Database session requested (placeholder)")
        yield db
    finally:
        # Example: db.close()
        logger.info("Database session closed (placeholder)")


def get_openai_client(config: Config = Depends(get_config)) -> Optional[OpenAI]:
    """Dependency to get OpenAI client."""
    if config.openai_api_key:
        try:
            client = OpenAI(api_key=config.openai_api_key)
            # Test connection (optional, can be done at startup)
            # client.models.list()
            logger.info("OpenAI client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI service is not available",
            )
    logger.warning("OpenAI API key not configured. OpenAI client will not be available.")
    return None


async def get_current_user(api_key: str = Depends(get_api_key)):
    """Dependency to get current user based on API key (placeholder)."""
    # In a real app, you might look up the user associated with the API key
    logger.info(f"Authenticated user with API key: {api_key[:5]}...")
    return {"api_key": api_key, "username": "authenticated_user"}  # Placeholder user object
