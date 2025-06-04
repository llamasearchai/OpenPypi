"""
OpenPypi - Complete Python Project Generator

A comprehensive Python project generator that creates production-ready Python packages
with modern development practices, automated testing, CI/CD pipelines, FastAPI integration,
Docker containerization, and OpenAI SDK integration.

Features:
- Complete project generation with proper structure
- FastAPI integration with authentication and documentation
- Docker containerization and docker-compose support
- OpenAI SDK integration for AI-powered code generation
- Automated testing framework with pytest
- Code quality tools (black, isort, flake8, pylint, mypy)
- Security scanning with bandit and safety
- Configuration management with TOML/JSON/environment variables
- CLI interface with multiple commands
- REST API with authentication and project management
- Stage pipeline system for modular workflows
- Provider architecture for external service integrations

Example Usage:
    >>> from openpypi import OpenPypi
    >>> from openpypi.core.config import Config
    >>>
    >>> config = Config(
    ...     project_name="My Awesome Project",
    ...     package_name="my_awesome_package",
    ...     author="Your Name",
    ...     email="you@example.com",
    ...     use_fastapi=True,
    ...     use_docker=True,
    ...     use_openai=True
    ... )
    >>>
    >>> generator = OpenPypi(config)
    >>> result = generator.generate_project()
    >>> print(f"Project created at: {result.output_path}")
"""

# Version information
try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = "1.0.0"
    __version_tuple__ = (1, 0, 0)

# Core functionality
from .core.config import Config, ConfigManager, load_config
from .core.context import Context
from .core.exceptions import (
    ConfigurationError,
    GenerationError,
    OpenPypiError,
    ProviderError,
    StageError,
    ValidationError,
)
from .core.generator import ProjectGenerator

# Provider system
from .providers import (
    ProviderRegistry,
    get_provider,
    list_providers,
)
from .providers import registry as provider_registry


# Provider access functions
def get_ai_provider(config=None):
    """Get AI provider instance."""
    return get_provider("ai", config)


def get_openai_provider(config=None):
    """Get OpenAI provider instance."""
    return get_provider("openai", config)


# Stage pipeline system
from .stages import (
    Pipeline,
    Stage,
    StageRegistry,
    StageResult,
    StageStatus,
    ValidationStage,
)
from .stages import registry as stage_registry

# API components (optional import)
try:
    from .api import create_app, get_current_user

    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    create_app = None
    get_current_user = None

# Security utilities
from .core.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    get_password_hash,
    validate_api_key,
    verify_password,
)
from .utils.formatters import CodeFormatter
from .utils.formatters import ProjectGenerator as FormatterProjectGenerator

# Utilities
from .utils.logger import get_logger, setup_logging


class OpenPypi:
    """
    Main OpenPypi project generator class.

    This is the primary interface for generating Python projects with OpenPypi.
    It orchestrates the entire generation process using the stage pipeline system.

    Attributes:
        config (Config): Project configuration
        pipeline (Pipeline): Generation pipeline
        context (Context): Execution context

    Example:
        >>> config = Config(project_name="MyApp", use_fastapi=True)
        >>> generator = OpenPypi(config)
        >>> result = generator.generate_project()
    """

    def __init__(self, config: Config):
        """
        Initialize the OpenPypi generator.

        Args:
            config: Project configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.config = config
        self.context = Context()
        self._setup_pipeline()

    def _setup_pipeline(self) -> None:
        """Set up the generation pipeline with appropriate stages."""
        from .stages.generation import GenerationStage
        from .stages.packaging import PackagingStage
        from .stages.testing import TestingStage
        from .stages.validation import ValidationStage

        self.pipeline = Pipeline("openpypi_generation")

        # Add stages in order
        self.pipeline.add_stage(ValidationStage("validation"))
        self.pipeline.add_stage(GenerationStage("generation"))

        # Note: Testing stage is disabled for now as it requires the generated project to be fully set up
        # if self.config.create_tests:
        #     self.pipeline.add_stage(TestingStage("testing"))

        self.pipeline.add_stage(PackagingStage("packaging"))

        # Set pipeline context
        self.pipeline.set_context(
            {"project_config": self.config, "output_dir": self.config.output_dir}
        )

    def validate_config(self) -> bool:
        """
        Validate the project configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            self.config.validate()
            return True
        except ValidationError:
            raise

    def generate_project(self) -> dict:
        """
        Generate the complete project.

        Returns:
            Dictionary containing generation results with keys:
            - output_path: Path to generated project
            - files_created: List of created files
            - directories_created: List of created directories
            - pipeline_results: Detailed pipeline execution results

        Raises:
            GenerationError: If project generation fails
        """
        try:
            # Validate configuration first
            self.validate_config()

            # Execute pipeline
            pipeline_results = self.pipeline.execute()

            # Check for failures
            failed_stages = [
                name
                for name, result in pipeline_results.items()
                if result.status == StageStatus.FAILED
            ]

            if failed_stages:
                raise GenerationError(f"Pipeline stages failed: {', '.join(failed_stages)}")

            # Extract results
            project_dir = self.pipeline.context.get("project_dir")
            files_created = []
            directories_created = []

            for result in pipeline_results.values():
                if result.data:
                    files_created.extend(result.data.get("files_created", []))
                    directories_created.extend(result.data.get("directories_created", []))

            return {
                "output_path": project_dir,
                "files_created": files_created,
                "directories_created": directories_created,
                "pipeline_results": pipeline_results,
                "success": True,
            }

        except Exception as e:
            raise GenerationError(f"Project generation failed: {e}") from e

    def get_pipeline_status(self) -> dict:
        """
        Get the current pipeline status.

        Returns:
            Dictionary with pipeline status information
        """
        return {
            "stages": list(self.pipeline.stages.keys()),
            "context": dict(self.pipeline.context),
            "results": dict(self.pipeline.results),
        }


# Export version and metadata
__author__ = "Nik Jois"
__email__ = "nikjois@llamasearch.ai"
__license__ = "MIT"
__description__ = (
    "Complete Python Project Generator with FastAPI, Docker, CI/CD, and OpenAI integration"
)
__url__ = "https://github.com/openpypi/openpypi"

# Public API
__all__ = [
    # Version
    "__version__",
    "__version_tuple__",
    # Main class
    "OpenPypi",
    # Core classes
    "Config",
    "ConfigManager",
    "ProjectGenerator",
    "Context",
    "load_config",
    # Exceptions
    "OpenPypiError",
    "ConfigurationError",
    "ValidationError",
    "GenerationError",
    "ProviderError",
    "StageError",
    # Stage system
    "Stage",
    "Pipeline",
    "StageResult",
    "StageStatus",
    "StageRegistry",
    "stage_registry",
    "ValidationStage",
    # Provider system
    "Provider",
    "ProviderRegistry",
    "provider_registry",
    "get_provider",
    "list_providers",
    "GitHubProvider",
    "DockerProvider",
    "CloudProvider",
    "AIProvider",
    "OpenAIProvider",
    "DatabaseProvider",
    # API (if available)
    "create_app",
    "get_current_user",
    "API_AVAILABLE",
    # Utilities
    "get_logger",
    "setup_logging",
    "CodeFormatter",
    "FormatterProjectGenerator",
    # Security
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_api_key",
    "validate_api_key",
    # Metadata
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "__url__",
]


def get_info() -> dict:
    """
    Get package information.

    Returns:
        Dictionary with package metadata
    """
    return {
        "name": "openpypi",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "url": __url__,
        "api_available": API_AVAILABLE,
        "features": {
            "fastapi": True,
            "docker": True,
            "openai": True,
            "testing": True,
            "security": True,
            "cli": True,
            "stages": True,
            "providers": True,
        },
    }


# Initialize logging
setup_logging()

# Get logger for this module
logger = get_logger(__name__)
logger.debug(f"OpenPypi v{__version__} initialized")
