"""
Configuration management for OpenPypi.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from ..utils.logger import get_logger
from .exceptions import ConfigurationError, ValidationError

logger = get_logger(__name__)


@dataclass
class Config:
    """Main configuration class for OpenPypi."""

    # Project metadata
    project_name: str = "example_project"
    package_name: str = "example_package"
    version: str = "0.1.0"
    author: str = "Author Name"
    email: str = "author@example.com"
    description: str = "A Python package"
    license: str = "MIT"
    python_requires: str = ">=3.8"

    # Paths
    output_dir: Path = field(default_factory=lambda: Path.cwd())
    template_dir: Optional[Path] = None

    # Features
    use_git: bool = True
    use_github_actions: bool = True
    use_docker: bool = True
    use_fastapi: bool = True
    use_openai: bool = True
    create_tests: bool = True
    test_framework: str = "pytest"

    # Dependencies
    dependencies: list = field(default_factory=list)
    dev_dependencies: list = field(default_factory=list)

    # Formatting
    use_black: bool = True
    use_isort: bool = True
    line_length: int = 100

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            if config_path.suffix.lower() == ".toml":
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
            elif config_path.suffix.lower() == ".json":
                with open(config_path, "r") as f:
                    data = json.load(f)
            else:
                raise ConfigurationError(f"Unsupported config file format: {config_path.suffix}")

            # Extract openpypi section if it exists
            if "openpypi" in data:
                data = data["openpypi"]

            return cls(**data)

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config_data = {}

        # Map environment variables to config fields
        env_mapping = {
            "OPENPYPI_PROJECT_NAME": "project_name",
            "OPENPYPI_PACKAGE_NAME": "package_name",
            "OPENPYPI_VERSION": "version",
            "OPENPYPI_AUTHOR": "author",
            "OPENPYPI_EMAIL": "email",
            "OPENPYPI_DESCRIPTION": "description",
            "OPENPYPI_LICENSE": "license",
            "OPENPYPI_PYTHON_REQUIRES": "python_requires",
            "OPENPYPI_OUTPUT_DIR": "output_dir",
            "OPENPYPI_USE_GIT": "use_git",
            "OPENPYPI_USE_GITHUB_ACTIONS": "use_github_actions",
            "OPENPYPI_USE_DOCKER": "use_docker",
            "OPENPYPI_USE_FASTAPI": "use_fastapi",
            "OPENPYPI_USE_OPENAI": "use_openai",
            "OPENPYPI_CREATE_TESTS": "create_tests",
            "OPENPYPI_TEST_FRAMEWORK": "test_framework",
            "OPENPYPI_USE_BLACK": "use_black",
            "OPENPYPI_USE_ISORT": "use_isort",
            "OPENPYPI_LINE_LENGTH": "line_length",
        }

        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_key in [
                    "use_git",
                    "use_github_actions",
                    "use_docker",
                    "use_fastapi",
                    "use_openai",
                    "create_tests",
                    "use_black",
                    "use_isort",
                ]:
                    value = value.lower() in ("true", "1", "yes", "on")
                elif config_key == "line_length":
                    value = int(value)
                elif config_key == "output_dir":
                    value = Path(value)

                config_data[config_key] = value

        return cls(**config_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                data[key] = str(value)
            else:
                data[key] = value
        return data

    def to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        data = self.to_dict()

        try:
            if config_path.suffix.lower() == ".json":
                with open(config_path, "w") as f:
                    json.dump(data, f, indent=2)
            elif config_path.suffix.lower() == ".toml":
                try:
                    import tomli_w

                    with open(config_path, "wb") as f:
                        tomli_w.dump({"openpypi": data}, f)
                except ImportError:
                    raise ConfigurationError("tomli_w required for writing TOML files")
            else:
                raise ConfigurationError(f"Unsupported config file format: {config_path.suffix}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def validate(self) -> None:
        """Validate configuration values."""
        errors = []

        # Validate required fields
        if not self.project_name:
            errors.append("project_name is required")

        if not self.package_name:
            errors.append("package_name is required")

        if not self.author:
            errors.append("author is required")

        if not self.email:
            errors.append("email is required")

        # Validate email format (basic)
        if self.email and "@" not in self.email:
            errors.append("email must be a valid email address")

        # Validate test framework
        if self.test_framework not in ["pytest", "unittest"]:
            errors.append("test_framework must be 'pytest' or 'unittest'")

        # Validate line length
        if self.line_length < 50 or self.line_length > 200:
            errors.append("line_length must be between 50 and 200")

        # Validate package name format
        if not self.package_name.replace("_", "").replace("-", "").isalnum():
            errors.append("package_name must be alphanumeric with underscores or hyphens only")

        if errors:
            raise ValidationError(f"Configuration validation failed: {'; '.join(errors)}")

    def update(self, **kwargs) -> None:
        """Update configuration with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown configuration key: {key}")


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Load configuration from various sources.

    Priority order:
    1. Provided config file path
    2. Environment variables
    3. Default config file in current directory
    4. Default configuration
    """
    # 1. Provided config file
    if config_path:
        return Config.from_file(config_path)

    # 2. Check for default config files
    default_files = ["openpypi.toml", "openpypi.json", ".openpypi.toml", ".openpypi.json"]
    for filename in default_files:
        config_file = Path(filename)
        if config_file.exists():
            logger.info(f"Loading configuration from {config_file}")
            return Config.from_file(config_file)

    # 3. Environment variables
    env_config = Config.from_env()
    if env_config.to_dict() != Config().to_dict():  # Check if any env vars were set
        logger.info("Loading configuration from environment variables")
        return env_config

    # 4. Default configuration
    logger.info("Using default configuration")
    return Config()
