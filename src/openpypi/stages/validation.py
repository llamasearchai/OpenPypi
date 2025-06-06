"""
Validation stage for input validation and configuration checking.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict

from ..core.config import Config
from ..core.exceptions import ValidationError
from . import Stage, StageResult, StageStatus, register_stage

logger = logging.getLogger(__name__)


@register_stage
class ValidationStage(Stage):
    """Stage for validating project configuration and inputs."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.dependencies = []  # No dependencies

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute validation stage."""
        try:
            logger.info("Starting validation stage")

            # Get configuration from context
            project_config = context.get("project_config")
            if not project_config:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message="No project configuration found in context",
                )

            # Convert to Config object if it's a dict
            if isinstance(project_config, dict):
                try:
                    config = Config(**project_config)
                except Exception as e:
                    return StageResult(
                        stage_name=self.name,
                        status=StageStatus.FAILED,
                        message=f"Invalid project configuration: {e}",
                    )
            else:
                config = project_config

            # Validation results
            validation_results = {
                "package_name": self._validate_package_name(config.package_name),
                "project_name": self._validate_project_name(config.project_name),
                "author": self._validate_author(config.author),
                "email": self._validate_email(config.email),
                "version": self._validate_version(config.version),
                "python_requires": self._validate_python_version(config.python_requires),
                "output_directory": self._validate_output_directory(context.get("output_dir")),
                "dependencies": self._validate_dependencies(config.dependencies),
            }

            # Check for any validation failures
            failed_validations = [k for k, v in validation_results.items() if not v["valid"]]

            if failed_validations:
                error_messages = []
                for field in failed_validations:
                    error_messages.append(f"{field}: {validation_results[field]['message']}")

                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"Validation failed: {'; '.join(error_messages)}",
                    data={"validation_results": validation_results},
                )

            # All validations passed
            logger.info("Validation stage completed successfully")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                message="All validations passed",
                data={"validated_config": config, "validation_results": validation_results},
            )

        except Exception as e:
            logger.error(f"Validation stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                message=f"Validation stage error: {e}",
                error=e,
            )

    def _validate_package_name(self, package_name: str) -> Dict[str, Any]:
        """Validate package name follows Python naming conventions."""
        if not package_name:
            return {"valid": False, "message": "Package name is required"}

        # Python package naming rules
        if not re.match(r"^[a-z][a-z0-9_]*$", package_name):
            return {
                "valid": False,
                "message": (
                    "Package name must start with lowercase letter and contain only lowercase letters, numbers, and underscores"
                ),
            }

        # Reserved keywords check
        python_keywords = {
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "exec",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "not",
            "or",
            "pass",
            "print",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        }

        if package_name in python_keywords:
            return {"valid": False, "message": f'Package name "{package_name}" is a Python keyword'}

        return {"valid": True, "message": "Package name is valid"}

    def _validate_project_name(self, project_name: str) -> Dict[str, Any]:
        """Validate project name."""
        if not project_name:
            return {"valid": False, "message": "Project name is required"}

        if len(project_name) > 100:
            return {"valid": False, "message": "Project name too long (max 100 characters)"}

        return {"valid": True, "message": "Project name is valid"}

    def _validate_author(self, author: str) -> Dict[str, Any]:
        """Validate author name."""
        if not author:
            return {"valid": False, "message": "Author name is required"}

        if len(author) > 100:
            return {"valid": False, "message": "Author name too long (max 100 characters)"}

        return {"valid": True, "message": "Author name is valid"}

    def _validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email address."""
        if not email:
            return {"valid": False, "message": "Email address is required"}

        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return {"valid": False, "message": "Invalid email address format"}

        return {"valid": True, "message": "Email address is valid"}

    def _validate_version(self, version: str) -> Dict[str, Any]:
        """Validate version string follows semantic versioning."""
        if not version:
            return {"valid": False, "message": "Version is required"}

        # Semantic versioning pattern
        semver_pattern = r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

        if not re.match(semver_pattern, version):
            return {
                "valid": False,
                "message": "Version must follow semantic versioning format (e.g., 1.0.0)",
            }

        return {"valid": True, "message": "Version is valid"}

    def _validate_python_version(self, python_requires: str) -> Dict[str, Any]:
        """Validate Python version requirement."""
        if not python_requires:
            return {"valid": False, "message": "Python version requirement is required"}

        # Common patterns: >=3.8, >=3.8,<4.0, ==3.8.*, etc.
        version_pattern = r"^(>=|>|<=|<|==|!=)\s*\d+\.\d+(\.\d+)?(\.\*)?(\s*,\s*(>=|>|<=|<|==|!=)\s*\d+\.\d+(\.\d+)?(\.\*)?)*$"

        if not re.match(version_pattern, python_requires):
            return {
                "valid": False,
                "message": 'Invalid Python version requirement format (e.g., ">=3.8")',
            }

        return {"valid": True, "message": "Python version requirement is valid"}

    def _validate_output_directory(self, output_dir: str) -> Dict[str, Any]:
        """Validate output directory."""
        if not output_dir:
            return {"valid": False, "message": "Output directory is required"}

        try:
            output_path = Path(output_dir)

            # Check if parent directory exists
            if not output_path.parent.exists():
                return {
                    "valid": False,
                    "message": f"Parent directory does not exist: {output_path.parent}",
                }

            # Check if we can write to the parent directory
            if not output_path.parent.is_dir():
                return {
                    "valid": False,
                    "message": f"Parent path is not a directory: {output_path.parent}",
                }

            return {"valid": True, "message": "Output directory is valid"}

        except Exception as e:
            return {"valid": False, "message": f"Invalid output directory: {e}"}

    def _validate_dependencies(self, dependencies: list) -> Dict[str, Any]:
        """Validate project dependencies."""
        if not isinstance(dependencies, list):
            return {"valid": False, "message": "Dependencies must be a list"}

        # Validate each dependency
        for dep in dependencies:
            if not isinstance(dep, str):
                return {"valid": False, "message": "Each dependency must be a string"}

            # Basic package name validation (can include version specifiers)
            if not re.match(
                r"^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]?(\[.*\])?([<>=!]+[0-9][a-zA-Z0-9._-]*)?$",
                dep,
            ):
                return {"valid": False, "message": f"Invalid dependency format: {dep}"}

        return {"valid": True, "message": "Dependencies are valid"}

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """Check if validation stage can execute."""
        # Validation stage can always execute
        return True
