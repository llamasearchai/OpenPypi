"""
Environment configuration manager with validation.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

from ..utils.logger import get_logger

logger = get_logger(__name__)


class EnvironmentConfig(BaseModel):
    """Environment configuration model."""

    # Core settings
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_organization: Optional[str] = Field(default=None, description="OpenAI organization")

    # PyPI settings
    pypi_api_token: Optional[str] = Field(default=None, description="PyPI API token")
    pypi_repository_url: str = Field(
        default="https://upload.pypi.org/legacy/", description="PyPI repository URL"
    )

    # Security settings
    secret_key: str = Field(default="dev-secret-key", description="Secret key for JWT")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")

    # Database settings
    database_url: str = Field(default="sqlite:///openpypi.db", description="Database URL")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            logger.warning("Secret key should be at least 32 characters long")
        return v

    @validator("openai_api_key")
    def validate_openai_key(cls, v):
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI API key should start with 'sk-'")
        return v


class EnvironmentManager:
    """Manages environment configuration and validation."""

    def __init__(self, env_file: Optional[Path] = None):
        self.env_file = env_file or Path(".env")
        self.config: Optional[EnvironmentConfig] = None
        self.load_environment()

    def load_environment(self) -> None:
        """Load environment configuration."""
        if self.env_file.exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment from {self.env_file}")
        else:
            logger.warning(f"Environment file {self.env_file} not found")

        self.config = EnvironmentConfig(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_organization=os.getenv("OPENAI_ORGANIZATION"),
            pypi_api_token=os.getenv("PYPI_API_TOKEN"),
            pypi_repository_url=os.getenv("PYPI_REPOSITORY_URL", "https://upload.pypi.org/legacy/"),
            secret_key=os.getenv("SECRET_KEY", "dev-secret-key"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///openpypi.db"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        )

    def validate_production_config(self) -> Dict[str, Any]:
        """Validate configuration for production environment."""
        issues = []

        if not self.config.openai_api_key:
            issues.append("OPENAI_API_KEY is not set")

        if not self.config.pypi_api_token:
            issues.append("PYPI_API_TOKEN is not set")

        if self.config.secret_key == "dev-secret-key":
            issues.append("SECRET_KEY is using default development value")

        if self.config.debug and self.config.environment == "production":
            issues.append("DEBUG mode should be disabled in production")

        return {"valid": len(issues) == 0, "issues": issues, "environment": self.config.environment}

    def get_config(self) -> EnvironmentConfig:
        """Get environment configuration."""
        if not self.config:
            self.load_environment()
        return self.config
