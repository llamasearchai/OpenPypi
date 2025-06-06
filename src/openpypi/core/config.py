"""
Enhanced configuration management for OpenPypi with comprehensive validation and type safety.
"""

import json
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import toml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils.logger import get_logger
from .exceptions import ConfigurationError, ValidationError

logger = get_logger(__name__)


@dataclass
class TemplateInfo:
    """Information about available project templates."""

    name: str
    description: str
    features: List[str]
    dependencies: List[str]
    framework: Optional[str] = None
    complexity: str = "simple"  # simple, intermediate, advanced


class ProjectConfig(BaseModel):
    """Enhanced project configuration model with comprehensive validation."""

    # Core project info
    project_name: str = Field(..., description="Project name", min_length=1, max_length=100)
    package_name: Optional[str] = Field(None, description="Python package name")
    description: str = Field("A Python package", description="Project description", max_length=500)
    version: str = Field("0.1.0", description="Initial version", pattern=r"^\d+\.\d+\.\d+$")

    # Author info
    author_name: str = Field("Your Name", description="Author name", max_length=100)
    author_email: str = Field("nikjois@llamasearch.ai", description="Author email")

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

    # AI and OpenAI settings
    use_ai_generation: bool = Field(False, description="Use AI for code generation")
    ai_provider: str = Field("openai", description="AI provider to use")
    ai_model: str = Field("gpt-3.5-turbo", description="AI model to use")

    # Advanced options
    framework: Optional[str] = Field(None, description="Web framework (fastapi, flask, etc.)")
    database: Optional[str] = Field(None, description="Database type")
    testing_framework: str = Field("pytest", description="Testing framework")

    # Quality and security settings
    enable_pre_commit: bool = Field(True, description="Enable pre-commit hooks")
    enable_security_scanning: bool = Field(True, description="Enable security scanning")
    enable_dependency_checking: bool = Field(
        True, description="Enable dependency vulnerability checking"
    )

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        """Validate project name format with comprehensive checks."""
        if not v or not v.strip():
            raise ValueError("Project name cannot be empty")

        v = v.strip()

        # Check length
        if len(v) < 2:
            raise ValueError("Project name must be at least 2 characters long")

        if len(v) > 100:
            raise ValueError("Project name must be less than 100 characters")

        # Allow letters, numbers, hyphens, underscores, dots
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", v):
            raise ValueError(
                "Project name must start with a letter and contain only letters, numbers, "
                "periods, hyphens, and underscores"
            )

        # Check for reserved names
        reserved_names = {
            "test",
            "tests",
            "src",
            "lib",
            "bin",
            "docs",
            "doc",
            "examples",
            "example",
            "sample",
            "demo",
            "temp",
            "tmp",
            "build",
            "dist",
            "python",
            "pip",
            "setuptools",
            "wheel",
            "pypi",
            "conda",
        }

        if v.lower() in reserved_names:
            raise ValueError(f"Project name '{v}' is reserved and cannot be used")

        return v

    @field_validator("package_name", mode="before")
    @classmethod
    def set_package_name(cls, v: Optional[str], info) -> str:
        """Set package name based on project name with enhanced validation."""
        if v is not None:
            return cls._validate_package_name(v)

        # Get project_name from the context if available
        project_name = ""
        if hasattr(info, "data") and info.data and "project_name" in info.data:
            project_name = info.data["project_name"]

        if not project_name:
            return "my_package"

        # Convert project name to valid Python package name
        package_name = project_name.replace("-", "_").replace(".", "_").replace(" ", "_").lower()

        # Ensure it's a valid Python identifier
        if not package_name.isidentifier() or package_name.startswith("_"):
            # If still invalid, prefix with 'pkg_'
            package_name = f"pkg_{package_name.lstrip('_')}"

        return cls._validate_package_name(package_name)

    @classmethod
    def _validate_package_name(cls, package_name: str) -> str:
        """Validate Python package name."""
        if not package_name.isidentifier():
            raise ValueError(f"Package name '{package_name}' is not a valid Python identifier")

        # Check for Python reserved words
        import keyword

        if keyword.iskeyword(package_name):
            raise ValueError(f"Package name '{package_name}' is a Python reserved word")

        # Check for common conflicts
        standard_library = {
            "sys",
            "os",
            "json",
            "time",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "operator",
            "math",
            "random",
            "string",
            "re",
            "urllib",
            "http",
            "email",
            "html",
            "xml",
            "sqlite3",
            "pathlib",
            "typing",
        }

        if package_name in standard_library:
            warnings.warn(
                f"Package name '{package_name}' conflicts with Python standard library module"
            )

        return package_name

    @field_validator("author_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Enhanced email validation."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        version_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?(?:\+[a-zA-Z0-9.]+)?$"
        if not re.match(version_pattern, v):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0, 1.0.0-alpha.1)")
        return v

    @field_validator("license_type")
    @classmethod
    def validate_license(cls, v: str) -> str:
        """Validate license type."""
        common_licenses = {
            "MIT",
            "Apache-2.0",
            "GPL-3.0",
            "BSD-3-Clause",
            "ISC",
            "GPL-2.0",
            "LGPL-2.1",
            "MPL-2.0",
            "CDDL-1.0",
            "EPL-2.0",
        }

        if v not in common_licenses:
            warnings.warn(f"License '{v}' is not a common open-source license")

        return v

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, v: str) -> str:
        """Validate AI provider."""
        supported_providers = {"openai", "anthropic", "google", "local"}
        if v.lower() not in supported_providers:
            raise ValueError(f"AI provider must be one of: {', '.join(supported_providers)}")
        return v.lower()

    @model_validator(mode="after")
    def validate_dependencies(self) -> "ProjectConfig":
        """Validate dependencies and check for conflicts."""
        all_deps = self.dependencies + self.dev_dependencies

        # Check for duplicate dependencies
        seen = set()
        duplicates = set()
        for dep in all_deps:
            dep_name = dep.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
            if dep_name in seen:
                duplicates.add(dep_name)
            seen.add(dep_name)

        if duplicates:
            warnings.warn(f"Duplicate dependencies found: {', '.join(duplicates)}")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """Create config from dictionary with validation."""
        return cls(**data)

    def get_normalized_names(self) -> Dict[str, str]:
        """Get normalized versions of project names."""
        return {
            "project_name": self.project_name,
            "package_name": self.package_name,
            "project_slug": self.project_name.lower().replace("_", "-"),
            "class_name": "".join(word.capitalize() for word in self.package_name.split("_")),
            "module_name": self.package_name.lower(),
            "constant_name": self.package_name.upper().replace("-", "_"),
        }

    def get_template_variables(self) -> Dict[str, Any]:
        """Get variables for template rendering."""
        names = self.get_normalized_names()
        return {
            **names,
            **self.to_dict(),
            "year": __import__("datetime").datetime.now().year,
            "features": self.get_enabled_features(),
        }

    def get_enabled_features(self) -> List[str]:
        """Get list of enabled features."""
        features = []

        if self.framework:
            features.append(f"framework_{self.framework}")
        if self.database:
            features.append(f"database_{self.database}")
        if self.use_ai_generation:
            features.append("ai_generation")
        if self.include_docker:
            features.append("docker")
        if self.include_ci:
            features.append("ci_cd")
        if self.enable_pre_commit:
            features.append("pre_commit")
        if self.enable_security_scanning:
            features.append("security_scanning")

        return features


def validate_config(config: ProjectConfig) -> Dict[str, Any]:
    """Comprehensive configuration validation with detailed feedback."""
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "suggestions": [],
        "security_recommendations": [],
    }

    # Check for placeholder values
    placeholders = {
        "your name": config.author_name.lower(),
        "your.email@example.com": config.author_email.lower(),
        "a python package": config.description.lower(),
    }

    for placeholder, value in placeholders.items():
        if placeholder in value:
            results["suggestions"].append(f"Replace placeholder value: {placeholder}")

    # Security recommendations
    if config.use_ai_generation and not config.enable_security_scanning:
        results["security_recommendations"].append(
            "Enable security scanning when using AI generation to check for potential vulnerabilities"
        )

    # Performance suggestions
    if config.framework == "fastapi" and "uvicorn" not in config.dependencies:
        results["suggestions"].append("Consider adding 'uvicorn' for FastAPI applications")

    # Testing recommendations
    if config.testing_framework == "pytest" and "pytest" not in config.dev_dependencies:
        results["suggestions"].append("Add 'pytest' to dev_dependencies for testing")

    return results


class Config(BaseSettings):
    """Enhanced main configuration class with comprehensive settings management."""

    model_config = SettingsConfigDict(
        env_prefix="OPENPYPI_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project metadata
    project_name: str = Field("openpypi", description="Name of the project")
    package_name: Optional[str] = Field(None, description="Python package name")
    author: str = Field("Nik Jois", description="Author name")
    email: str = Field("nikjois@llamasearch.ai", description="Author email")
    description: Optional[str] = Field(None, description="Project description")
    version: str = Field("0.1.0", description="Project version")
    license: str = Field("MIT", description="License type")
    python_requires: str = Field(">=3.8", description="Python version requirement")

    # Output configuration
    output_dir: Path = Field(Path.cwd(), description="Output directory")

    # Feature flags with enhanced options
    use_fastapi: bool = Field(False, description="Enable FastAPI integration")
    use_openai: bool = Field(False, description="Enable OpenAI integration")
    use_docker: bool = Field(False, description="Enable Docker support")
    use_github_actions: bool = Field(False, description="Enable GitHub Actions")
    create_tests: bool = Field(True, description="Generate test files")
    use_git: bool = Field(True, description="Initialize git repository")
    use_database: bool = Field(False, description="Enable database integration")
    use_async: bool = Field(False, description="Enable async support")
    use_type_hints: bool = Field(True, description="Use comprehensive type hints")

    # Quality and security
    enable_linting: bool = Field(True, description="Enable code linting")
    enable_formatting: bool = Field(True, description="Enable code formatting")
    enable_pre_commit: bool = Field(True, description="Enable pre-commit hooks")
    enable_security_scanning: bool = Field(True, description="Enable security scanning")

    # Testing configuration
    test_framework: str = Field("pytest", description="Test framework to use")
    coverage_threshold: float = Field(80.0, description="Minimum test coverage percentage")
    enable_performance_tests: bool = Field(False, description="Enable performance testing")

    # Dependencies with categories
    dependencies: List[str] = Field(default_factory=list, description="Project dependencies")
    dev_dependencies: List[str] = Field(
        default_factory=list, description="Development dependencies"
    )
    optional_dependencies: Dict[str, List[str]] = Field(
        default_factory=dict, description="Optional dependency groups"
    )

    # Cloud and deployment
    cloud_provider: Optional[str] = Field(None, description="Cloud provider (aws, gcp, azure)")
    kubernetes_enabled: bool = Field(False, description="Enable Kubernetes support")
    docker_registry: Optional[str] = Field(None, description="Docker registry URL")

    # AI configuration
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    ai_model: str = Field("gpt-3.5-turbo", description="AI model to use")
    max_ai_requests: int = Field(100, description="Maximum AI requests per session")

    # API configuration
    api_host: str = Field("0.0.0.0", description="API host")
    api_port: int = Field(8000, description="API port")
    api_reload: bool = Field(False, description="Enable API auto-reload")
    api_workers: int = Field(1, description="Number of API workers")

    # Security configuration
    allowed_hosts: List[str] = Field(["*"], description="Allowed hosts")
    cors_origins: List[str] = Field(["*"], description="CORS allowed origins")
    secret_key: Optional[str] = Field(None, description="Secret key for sessions")
    jwt_secret: Optional[str] = Field(None, description="JWT secret key")

    # App configuration
    app_env: str = Field("development", description="Application environment")
    log_level: str = Field("INFO", description="Logging level")
    debug: bool = Field(False, description="Enable debug mode")

    # Rate limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests: int = Field(100, description="Requests per minute limit")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")

    # Monitoring and observability
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    enable_tracing: bool = Field(False, description="Enable distributed tracing")
    metrics_port: int = Field(9090, description="Metrics endpoint port")

    # Security/testing overrides (for API/tests only)
    api_keys: List[str] = Field(default_factory=list, description="API keys for test/dev override")
    fake_users_db_override: Optional[dict] = Field(
        default=None, description="Override user DB for testing"
    )
    allow_overwrite: bool = Field(
        default=False, description="Allow overwriting existing directories"
    )

    @field_validator("package_name", mode="before")
    @classmethod
    def set_package_name(cls, v, info):
        """Set package name from project name if not provided."""
        if v is None and hasattr(info, "data") and info.data and "project_name" in info.data:
            return info.data["project_name"].replace("-", "_").lower()
        return v

    @field_validator("description", mode="before")
    @classmethod
    def set_description(cls, v, info):
        """Set description from project name if not provided."""
        if v is None and hasattr(info, "data") and info.data and "project_name" in info.data:
            return f"A Python package for {info.data['project_name']}"
        return v

    @field_validator("output_dir", mode="before")
    @classmethod
    def convert_output_dir(cls, v):
        """Convert output_dir to Path object."""
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    @field_validator("test_framework")
    @classmethod
    def validate_test_framework(cls, v):
        """Validate test framework choice."""
        allowed = {"pytest", "unittest", "nose2"}
        if v not in allowed:
            raise ValueError(f"Test framework must be one of: {', '.join(allowed)}")
        return v

    @field_validator("cloud_provider")
    @classmethod
    def validate_cloud_provider(cls, v):
        """Validate cloud provider choice."""
        if v is None:
            return v
        allowed = {"aws", "gcp", "azure", "digitalocean", "linode"}
        if v.lower() not in allowed:
            raise ValueError(f"Cloud provider must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v):
        """Validate application environment."""
        allowed = {"development", "testing", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"App environment must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {', '.join(allowed)}")
        return v.upper()

    def validate(self) -> None:
        """Comprehensive configuration validation."""
        errors = []
        warnings = []

        # Validate project name
        if not self.project_name:
            errors.append("Project name is required")
        elif not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", self.project_name):
            errors.append(
                "Project name must start with a letter and contain only alphanumeric characters, "
                "periods, hyphens, and underscores"
            )

        # Validate package name
        if not self.package_name:
            errors.append("Package name is required")
        elif not self.package_name.isidentifier():
            errors.append("Package name must be a valid Python identifier")

        # Validate email format
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, self.email):
            errors.append("Invalid email format")

        # Validate version format
        if not re.match(r"^\d+\.\d+\.\d+", self.version):
            errors.append("Version must start with semantic versioning format (X.Y.Z)")

        # Validate coverage threshold
        if not 0 <= self.coverage_threshold <= 100:
            errors.append("Coverage threshold must be between 0 and 100")

        # Production environment checks
        if self.app_env == "production":
            if not self.secret_key:
                warnings.append("Secret key should be set in production")
            if self.debug:
                warnings.append("Debug mode should be disabled in production")
            if "*" in self.allowed_hosts:
                warnings.append("Allowed hosts should be restricted in production")

        # Security warnings
        if self.use_openai and not self.openai_api_key:
            warnings.append("OpenAI API key is required when OpenAI integration is enabled")

        if errors:
            raise ValidationError(f"Configuration validation failed: {'; '.join(errors)}")

        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")

    def get_runtime_dependencies(self) -> List[str]:
        """Get complete list of runtime dependencies based on configuration."""
        deps = list(self.dependencies)

        # Add framework dependencies
        if self.use_fastapi:
            deps.extend(
                ["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0", "python-multipart>=0.0.6"]
            )

        # Add AI dependencies
        if self.use_openai:
            deps.extend(["openai>=1.3.0", "tiktoken>=0.5.0"])

        # Add database dependencies
        if self.use_database:
            deps.extend(["sqlalchemy>=2.0.0", "alembic>=1.12.0"])

        # Add async dependencies
        if self.use_async:
            deps.extend(["aiofiles>=23.0.0", "asyncio-mqtt>=0.13.0"])

        return list(set(deps))  # Remove duplicates

    def get_dev_dependencies(self) -> List[str]:
        """Get complete list of development dependencies."""
        dev_deps = list(self.dev_dependencies)

        # Testing dependencies
        if self.test_framework == "pytest":
            dev_deps.extend(
                [
                    "pytest>=7.4.0",
                    "pytest-cov>=4.1.0",
                    "pytest-asyncio>=0.21.0" if self.use_async else None,
                ]
            )

        # Code quality dependencies
        if self.enable_formatting:
            dev_deps.extend(["black>=23.0.0", "isort>=5.12.0"])

        if self.enable_linting:
            dev_deps.extend(["flake8>=6.0.0", "mypy>=1.7.0", "pylint>=3.0.0"])

        # Security dependencies
        if self.enable_security_scanning:
            dev_deps.extend(["bandit>=1.7.5", "safety>=2.3.0"])

        # Pre-commit dependencies
        if self.enable_pre_commit:
            dev_deps.append("pre-commit>=3.0.0")

        return [dep for dep in dev_deps if dep is not None]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()

    def to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to file with proper serialization."""
        file_path = Path(file_path)
        data = self.to_dict()

        # Convert Path objects to strings for serialization
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)

        if file_path.suffix.lower() == ".json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        else:
            # Default to TOML
            with open(file_path, "w", encoding="utf-8") as f:
                toml.dump(data, f)

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "Config":
        """Load configuration from file with error handling."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")

        try:
            if file_path.suffix.lower() == ".json":
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                # Default to TOML
                with open(file_path, encoding="utf-8") as f:
                    data = toml.load(f)

            return cls(**data)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {file_path}: {e}")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()


class ConfigManager:
    """Enhanced configuration manager with template support and validation."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.cwd()
        self.templates: Dict[str, TemplateInfo] = self._load_templates()

    def _load_templates(self) -> Dict[str, TemplateInfo]:
        """Load available project templates."""
        return {
            "basic": TemplateInfo(
                name="basic",
                description="Basic Python package with minimal dependencies",
                features=["basic_structure", "testing", "documentation"],
                dependencies=[],
            ),
            "fastapi": TemplateInfo(
                name="fastapi",
                description="FastAPI web application with async support",
                features=["fastapi", "async", "api_docs", "testing"],
                dependencies=["fastapi", "uvicorn"],
                framework="fastapi",
                complexity="intermediate",
            ),
            "ml": TemplateInfo(
                name="ml",
                description="Machine learning project with common ML libraries",
                features=["ml", "jupyter", "data_analysis", "testing"],
                dependencies=["numpy", "pandas", "scikit-learn", "matplotlib"],
                complexity="intermediate",
            ),
            "cli": TemplateInfo(
                name="cli",
                description="Command-line interface application",
                features=["cli", "click", "testing", "packaging"],
                dependencies=["click", "rich"],
                complexity="simple",
            ),
        }

    def get_templates(self) -> Dict[str, TemplateInfo]:
        """Get available templates."""
        return self.templates

    def get_template(self, name: str) -> Optional[TemplateInfo]:
        """Get specific template by name."""
        return self.templates.get(name)

    def load_config(self, name: str = "default") -> Config:
        """Load a named configuration with fallback."""
        for ext in [".toml", ".json"]:
            config_file = self.config_dir / f"{name}{ext}"
            if config_file.exists():
                return Config.from_file(config_file)

        # Return default config
        logger.info(f"No configuration file found for '{name}', using defaults")
        return Config()

    def save_config(self, config: Config, name: str = "default") -> None:
        """Save a named configuration."""
        config_file = self.config_dir / f"{name}.toml"
        config.to_file(config_file)
        logger.info(f"Configuration saved to {config_file}")

    def list_configs(self) -> List[str]:
        """List available configurations."""
        configs = set()
        for pattern in ["*.toml", "*.json"]:
            for file_path in self.config_dir.glob(pattern):
                configs.add(file_path.stem)
        return sorted(configs)

    def validate_config(self, config: Config) -> Dict[str, Any]:
        """Validate configuration comprehensively."""
        try:
            config.validate()
            return {"valid": True, "errors": [], "warnings": []}
        except ValidationError as e:
            return {"valid": False, "errors": [str(e)], "warnings": []}


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from file or environment with fallback."""
    if config_path:
        return Config.from_file(config_path)

    # Look for default config files
    default_files = [
        "openpypi.toml",
        "openpypi.json",
        ".openpypi.toml",
        ".openpypi.json",
        "pyproject.toml",
    ]

    for filename in default_files:
        if Path(filename).exists():
            try:
                return Config.from_file(filename)
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")
                continue

    # Return config from environment
    logger.info("Loading configuration from environment variables")
    return Config.from_env()


def get_settings() -> Config:
    """Get application settings (alias for load_config for compatibility)."""
    return load_config()
