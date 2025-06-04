"""
Configuration management for OpenPypi.
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import toml
from pydantic import BaseModel, Field, field_validator, validator
from pydantic_settings import BaseSettings

from ..utils.logger import get_logger
from .exceptions import ConfigurationError, ValidationError

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
    dev_dependencies: List[str] = Field(
        default_factory=list, description="Development dependencies"
    )

    # OpenAI settings
    use_ai_generation: bool = Field(False, description="Use AI for code generation")
    ai_provider: str = Field("openai", description="AI provider to use")

    # Advanced options
    framework: Optional[str] = Field(None, description="Web framework (fastapi, flask, etc.)")
    database: Optional[str] = Field(None, description="Database type")

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v):
        """Validate project name format."""
        if not v:
            raise ValueError("Project name cannot be empty")

        # Allow letters, numbers, hyphens, underscores
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Project name must start with a letter and contain only letters, numbers, hyphens, and underscores"
            )

        return v

    @field_validator("package_name", mode="before")
    @classmethod 
    def set_package_name(cls, v, info):
        """Set package name based on project name if not provided."""
        if v is not None:
            return v

        # Get project_name from the context if available
        project_name = ""
        if info.data and "project_name" in info.data:
            project_name = info.data["project_name"]
        
        if not project_name:
            return "my_package"

        # Convert project name to valid Python package name
        # Keep underscores, convert hyphens to underscores, ensure valid Python identifier
        package_name = project_name.replace("-", "_").lower()

        # Ensure it's a valid Python identifier
        if not package_name.isidentifier() or package_name.startswith("_"):
            # If still invalid, prefix with 'pkg_'
            package_name = f"pkg_{package_name.lstrip('_')}"

        return package_name

    @field_validator("author_email")
    @classmethod
    def validate_email(cls, v):
        """Basic email validation."""
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """Create config from dictionary."""
        return cls(**data)

    def get_normalized_names(self) -> Dict[str, str]:
        """Get normalized versions of project names."""
        return {
            "project_name": self.project_name,
            "package_name": self.package_name,
            "project_slug": self.project_name.lower().replace("_", "-"),
            "class_name": "".join(word.capitalize() for word in self.package_name.split("_")),
            "module_name": self.package_name.lower(),
        }


def validate_config(config: ProjectConfig) -> Dict[str, Any]:
    """Validate configuration and return validation results."""
    results = {"valid": True, "errors": [], "warnings": [], "suggestions": []}

    # Check for common issues
    names = config.get_normalized_names()

    # Check if package name conflicts with common Python modules
    common_modules = {"sys", "os", "json", "time", "datetime", "collections", "itertools"}
    if names["package_name"] in common_modules:
        results["warnings"].append(
            f"Package name '{names['package_name']}' conflicts with standard library module"
        )

    # Check if project name is too short
    if len(config.project_name) < 3:
        results["warnings"].append("Project name is very short, consider a more descriptive name")

    # Check for placeholder values
    placeholders = ["your name", "your.email@example.com", "a python package"]
    if any(
        placeholder in str(getattr(config, field, "")).lower()
        for field in ["author_name", "author_email", "description"]
        for placeholder in placeholders
    ):
        results["suggestions"].append("Update placeholder values for author and description")

    return results


class Config(BaseSettings):
    """Main configuration class for OpenPypi projects."""
    
    # Project metadata
    project_name: str = Field("openpypi", description="Name of the project")
    package_name: Optional[str] = Field(None, description="Python package name")
    author: str = Field("Nikhil Jois", description="Author name")
    email: str = Field("nikjois@llamasearch.ai", description="Author email")
    description: Optional[str] = Field(None, description="Project description")
    version: str = Field("0.1.0", description="Project version")
    license: str = Field("MIT", description="License type")
    python_requires: str = Field(">=3.8", description="Python version requirement")
    
    # Output configuration
    output_dir: Path = Field(Path.cwd(), description="Output directory")
    
    # Feature flags
    use_fastapi: bool = Field(False, description="Enable FastAPI integration")
    use_openai: bool = Field(False, description="Enable OpenAI integration")
    use_docker: bool = Field(False, description="Enable Docker support")
    use_github_actions: bool = Field(False, description="Enable GitHub Actions")
    create_tests: bool = Field(True, description="Generate test files")
    use_git: bool = Field(True, description="Initialize git repository")
    use_database: bool = Field(False, description="Enable database integration")
    
    # Testing configuration
    test_framework: str = Field("pytest", description="Test framework to use")
    
    # Dependencies
    dependencies: List[str] = Field(default_factory=list, description="Project dependencies")
    dev_dependencies: List[str] = Field(default_factory=list, description="Development dependencies")
    
    # Cloud and deployment
    cloud_provider: Optional[str] = Field(None, description="Cloud provider")
    kubernetes_enabled: bool = Field(False, description="Enable Kubernetes support")
    
    # AI configuration
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    
    # API configuration  
    api_host: str = Field("0.0.0.0", description="API host")
    api_port: int = Field(8000, description="API port")
    api_reload: bool = Field(False, description="Enable API auto-reload")
    
    # Security configuration
    allowed_hosts: List[str] = Field(["*"], description="Allowed hosts")
    cors_origins: List[str] = Field(["*"], description="CORS allowed origins")
    
    # App configuration
    app_env: str = Field("development", description="Application environment")
    log_level: str = Field("INFO", description="Logging level")
    
    class Config:
        env_prefix = "OPENPYPI_"
        case_sensitive = False
        
    @validator("package_name", always=True)
    def set_package_name(cls, v, values):
        """Set package name from project name if not provided."""
        if v is None and "project_name" in values:
            return values["project_name"].replace("-", "_").lower()
        return v
    
    @validator("description", always=True)
    def set_description(cls, v, values):
        """Set description from project name if not provided."""
        if v is None and "project_name" in values:
            return f"A Python package for {values['project_name']}"
        return v
    
    @validator("output_dir", pre=True)
    def convert_output_dir(cls, v):
        """Convert output_dir to Path object."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    def validate(self) -> None:
        """Validate the configuration."""
        errors = []
        
        # Validate project name
        if not self.project_name:
            errors.append("Project name is required")
        elif not self.project_name.replace("-", "").replace("_", "").isalnum():
            errors.append("Project name must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate package name
        if not self.package_name:
            errors.append("Package name is required")
        elif not self.package_name.replace("_", "").isalnum():
            errors.append("Package name must contain only alphanumeric characters and underscores")
        
        # Validate email format
        if "@" not in self.email:
            errors.append("Invalid email format")
        
        # Validate version format
        version_parts = self.version.split(".")
        if len(version_parts) != 3 or not all(part.isdigit() for part in version_parts):
            errors.append("Version must be in format X.Y.Z where X, Y, Z are numbers")
        
        # Validate test framework
        if self.test_framework not in ["pytest", "unittest"]:
            errors.append("Test framework must be 'pytest' or 'unittest'")
        
        # Validate cloud provider
        if self.cloud_provider and self.cloud_provider not in ["aws", "gcp", "azure"]:
            errors.append("Cloud provider must be 'aws', 'gcp', or 'azure'")
        
        if errors:
            raise ValidationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()
    
    def to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == ".json":
            with open(file_path, "w") as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
        else:
            # Default to TOML
            with open(file_path, "w") as f:
                toml.dump(self.to_dict(), f)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "Config":
        """Load configuration from file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        
        try:
            if file_path.suffix.lower() == ".json":
                with open(file_path) as f:
                    data = json.load(f)
            else:
                # Default to TOML
                with open(file_path) as f:
                    data = toml.load(f)
            
            return cls(**data)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {file_path}: {e}")
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()


class ConfigManager:
    """Configuration manager for handling multiple configurations."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.cwd()
    
    def load_config(self, name: str = "default") -> Config:
        """Load a named configuration."""
        config_file = self.config_dir / f"{name}.toml"
        if config_file.exists():
            return Config.from_file(config_file)
        
        # Try JSON format
        config_file = self.config_dir / f"{name}.json"
        if config_file.exists():
            return Config.from_file(config_file)
        
        # Return default config
        return Config()
    
    def save_config(self, config: Config, name: str = "default") -> None:
        """Save a named configuration."""
        config_file = self.config_dir / f"{name}.toml"
        config.to_file(config_file)
    
    def list_configs(self) -> List[str]:
        """List available configurations."""
        configs = []
        for file_path in self.config_dir.glob("*.toml"):
            configs.append(file_path.stem)
        for file_path in self.config_dir.glob("*.json"):
            if file_path.stem not in configs:
                configs.append(file_path.stem)
        return sorted(configs)


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from file or environment."""
    if config_path:
        return Config.from_file(config_path)
    
    # Look for default config files
    default_files = ["openpypi.toml", "openpypi.json", ".openpypi.toml", ".openpypi.json"]
    for filename in default_files:
        if Path(filename).exists():
            return Config.from_file(filename)
    
    # Return config from environment
    return Config.from_env()


def get_settings() -> Config:
    """Get application settings (alias for load_config for compatibility)."""
    return load_config()
