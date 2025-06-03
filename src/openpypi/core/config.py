"""
Configuration management for OpenPypi.
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from ..utils.logger import get_logger
from .exceptions import ConfigurationError, ValidationError
from pydantic import BaseModel, validator, Field

logger = get_logger(__name__)


class ProjectConfig(BaseModel):
    """Project configuration model."""
    
    # Core project info
    project_name: str = Field(..., description="Project name")
    package_name: Optional[str] = Field(None, description="Python package name")
    description: str = Field("A Python package", description="Project description")
    version: str = Field("0.1.0", description="Initial version")
    
    # Author info
    author_name: str = Field("Your Name", description="Author name")
    author_email: str = Field("your.email@example.com", description="Author email")
    
    # License and metadata
    license_type: str = Field("MIT", description="License type")
    python_requires: str = Field(">=3.8", description="Python version requirement")
    
    # Project structure
    use_src_layout: bool = Field(True, description="Use src/ layout")
    include_tests: bool = Field(True, description="Include test suite")
    include_docs: bool = Field(True, description="Include documentation")
    include_ci: bool = Field(True, description="Include CI/CD configuration")
    include_docker: bool = Field(False, description="Include Docker configuration")
    
    # Dependencies
    dependencies: List[str] = Field(default_factory=list, description="Runtime dependencies")
    dev_dependencies: List[str] = Field(default_factory=list, description="Development dependencies")
    
    # OpenAI settings
    use_ai_generation: bool = Field(False, description="Use AI for code generation")
    ai_provider: str = Field("openai", description="AI provider to use")
    
    # Advanced options
    framework: Optional[str] = Field(None, description="Web framework (fastapi, flask, etc.)")
    database: Optional[str] = Field(None, description="Database type")
    
    @validator('project_name')
    def validate_project_name(cls, v):
        """Validate project name format."""
        if not v:
            raise ValueError("Project name cannot be empty")
        
        # Allow letters, numbers, hyphens, underscores
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError("Project name must start with a letter and contain only letters, numbers, hyphens, and underscores")
        
        return v
    
    @validator('package_name', always=True)
    def set_package_name(cls, v, values):
        """Set package name based on project name if not provided."""
        if v is not None:
            return v
        
        project_name = values.get('project_name', '')
        if not project_name:
            return 'my_package'
        
        # Convert project name to valid Python package name
        # Keep underscores, convert hyphens to underscores, ensure valid Python identifier
        package_name = project_name.replace('-', '_').lower()
        
        # Ensure it's a valid Python identifier
        if not package_name.isidentifier() or package_name.startswith('_'):
            # If still invalid, prefix with 'pkg_'
            package_name = f"pkg_{package_name.lstrip('_')}"
        
        return package_name
    
    @validator('author_email')
    def validate_email(cls, v):
        """Basic email validation."""
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError("Invalid email format")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """Create config from dictionary."""
        return cls(**data)
    
    def get_normalized_names(self) -> Dict[str, str]:
        """Get normalized versions of project names."""
        return {
            'project_name': self.project_name,
            'package_name': self.package_name,
            'project_slug': self.project_name.lower().replace('_', '-'),
            'class_name': ''.join(word.capitalize() for word in self.package_name.split('_')),
            'module_name': self.package_name.lower(),
        }


def load_config(config_path: Optional[Path] = None) -> ProjectConfig:
    """Load configuration from file or environment."""
    if config_path and config_path.exists():
        # TODO: Implement file loading (TOML, YAML, JSON)
        pass
    
    # For now, return default config
    return ProjectConfig(
        project_name=os.getenv('PROJECT_NAME', 'my-project'),
        author_name=os.getenv('AUTHOR_NAME', 'Your Name'),
        author_email=os.getenv('AUTHOR_EMAIL', 'your.email@example.com'),
    )


def validate_config(config: ProjectConfig) -> Dict[str, Any]:
    """Validate configuration and return validation results."""
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'suggestions': []
    }
    
    # Check for common issues
    names = config.get_normalized_names()
    
    # Check if package name conflicts with common Python modules
    common_modules = {'sys', 'os', 'json', 'time', 'datetime', 'collections', 'itertools'}
    if names['package_name'] in common_modules:
        results['warnings'].append(f"Package name '{names['package_name']}' conflicts with standard library module")
    
    # Check if project name is too short
    if len(config.project_name) < 3:
        results['warnings'].append("Project name is very short, consider a more descriptive name")
    
    # Check for placeholder values
    placeholders = ['your name', 'your.email@example.com', 'a python package']
    if any(placeholder in str(getattr(config, field, '')).lower() 
           for field in ['author_name', 'author_email', 'description'] 
           for placeholder in placeholders):
        results['suggestions'].append("Update placeholder values for author and description")
    
    return results


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

    # Security/API
    api_keys: list = field(default_factory=list)
    fake_users_db_override: dict = field(default_factory=dict)
    openai_api_key: Optional[str] = None
    access_token_expire_minutes: int = 30

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
            "OPENAI_API_KEY": "openai_api_key",
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

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return getattr(self, key, default)


class ConfigManager:
    """Manager for configuration operations."""

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()

    @property
    def config(self) -> Config:
        """Get the current configuration."""
        return self._config

    def load_from_file(self, config_path: Union[str, Path]) -> None:
        """Load configuration from file."""
        self._config = Config.from_file(config_path)

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        self._config = Config.from_env()

    def update_config(self, **kwargs) -> None:
        """Update configuration with new values."""
        self._config.update(**kwargs)

    def validate_config(self) -> None:
        """Validate the current configuration."""
        self._config.validate()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting."""
        return getattr(self._config, key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set a configuration setting."""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
        else:
            logger.warning(f"Unknown configuration key: {key}")

    def get_config(self) -> Config:
        """Get the current configuration (alias for config property)."""
        return self._config
