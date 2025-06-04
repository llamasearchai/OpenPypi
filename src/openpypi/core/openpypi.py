"""
OpenPypi Core - Main orchestration and pipeline management.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from openpypi.core.config import ConfigManager
from openpypi.core.context import PackageContext
from openpypi.core.exceptions import OpenPypiException, ValidationError
from openpypi.core.generator import ProjectGenerator
from openpypi.providers import get_provider
from openpypi.stages import Pipeline, StageStatus
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class OpenPypi:
    """
    Main OpenPypi orchestrator for complete Python project generation.

    This class coordinates the entire process of generating a complete Python project
    with FastAPI, Docker, CI/CD, tests, documentation, and OpenAI integration.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize OpenPypi orchestrator."""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        self.generator = ProjectGenerator(self.config)
        self.context: Optional[PackageContext] = None

        # Initialize providers
        self.ai_provider = get_provider("openai", self.config.get("openai", {}))
        self.docker_provider = get_provider("docker", self.config.get("docker", {}))
        self.github_provider = get_provider("github", self.config.get("github", {}))

        logger.info("OpenPypi orchestrator initialized")

    async def generate_complete_project(
        self, idea: str, output_dir: Path, package_name: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a complete Python project from an idea.

        Args:
            idea: The project idea or description
            output_dir: Directory to generate the project in
            package_name: Name for the package (auto-generated if not provided)
            **kwargs: Additional configuration options

        Returns:
            Dict containing project generation results and metadata
        """
        try:
            logger.info(f"Starting complete project generation for idea: {idea}")

            # Create package context
            self.context = await self._create_context(idea, output_dir, package_name, **kwargs)

            # Create generation pipeline
            pipeline = self._create_generation_pipeline()

            # Execute pipeline
            results = await pipeline.execute_async()

            # Generate project summary
            summary = self._generate_project_summary(results)

            logger.info("Project generation completed successfully")
            return {
                "success": True,
                "context": self.context.to_dict(),
                "pipeline_results": results,
                "project_summary": summary,
                "output_directory": str(output_dir),
                "package_name": self.context.package_name,
            }

        except Exception as e:
            logger.error(f"Project generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "context": self.context.to_dict() if self.context else None,
            }

    async def _create_context(
        self, idea: str, output_dir: Path, package_name: Optional[str] = None, **kwargs
    ) -> PackageContext:
        """Create and configure package context."""
        # Auto-generate package name if not provided
        if not package_name:
            package_name = self._generate_package_name(idea)

        context = PackageContext(
            package_name=package_name,
            idea=idea,
            output_dir=output_dir,
            config=self.config,
            **kwargs,
        )

        # Set provider instances
        context.providers = {
            "ai": self.ai_provider,
            "docker": self.docker_provider,
            "github": self.github_provider,
        }

        logger.info(f"Created context for package: {package_name}")
        return context

    def _create_generation_pipeline(self) -> Pipeline:
        """Create the complete project generation pipeline."""
        pipeline = Pipeline("complete_project_generation", self.config)

        # Set pipeline context
        pipeline.set_context(self.context.to_dict())

        # Add stages in dependency order
        from openpypi.stages.p1_conceptualizer import ConceptualizerStage
        from openpypi.stages.p2_architect import ArchitectStage
        from openpypi.stages.p3_packager import PackagerStage
        from openpypi.stages.p4_validator import ValidatorStage
        from openpypi.stages.p5_documentarian import DocumentarianStage
        from openpypi.stages.p6_deployer import DeployerStage
        from openpypi.stages.p7_refiner import RefinerStage

        pipeline.add_stage(ConceptualizerStage("conceptualizer", self.config))
        pipeline.add_stage(ArchitectStage("architect", self.config))
        pipeline.add_stage(PackagerStage("packager", self.config))
        pipeline.add_stage(ValidatorStage("validator", self.config))
        pipeline.add_stage(DocumentarianStage("documentarian", self.config))
        pipeline.add_stage(DeployerStage("deployer", self.config))
        pipeline.add_stage(RefinerStage("refiner", self.config))

        logger.info("Created complete generation pipeline")
        return pipeline

    def _generate_package_name(self, idea: str) -> str:
        """Generate a valid package name from the idea."""
        # Simple package name generation
        import re

        # Extract meaningful words
        words = re.findall(r"\b[a-zA-Z]+\b", idea.lower())

        # Take first few words and create package name
        package_words = words[:3] if len(words) >= 3 else words
        package_name = "_".join(package_words)

        # Ensure it's a valid Python identifier
        if not package_name or not package_name[0].isalpha():
            package_name = f"generated_{package_name}" if package_name else "generated_package"

        # Remove any invalid characters
        package_name = re.sub(r"[^a-zA-Z0-9_]", "_", package_name)

        logger.info(f"Generated package name: {package_name}")
        return package_name

    def _generate_project_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the project generation results."""
        successful_stages = [
            name for name, result in results.items() if result.status == StageStatus.SUCCESS
        ]

        failed_stages = [
            name for name, result in results.items() if result.status == StageStatus.FAILED
        ]

        total_time = sum(result.execution_time for result in results.values())

        return {
            "total_stages": len(results),
            "successful_stages": len(successful_stages),
            "failed_stages": len(failed_stages),
            "execution_time": total_time,
            "success_rate": len(successful_stages) / len(results) if results else 0,
            "stage_details": {
                name: {
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "message": result.message,
                }
                for name, result in results.items()
            },
        }

    async def validate_project(self, project_dir: Path) -> Dict[str, Any]:
        """
        Validate an existing project structure and quality.

        Args:
            project_dir: Path to the project directory

        Returns:
            Dict containing validation results
        """
        try:
            logger.info(f"Validating project at: {project_dir}")

            # Load project configuration
            config_path = project_dir / "pyproject.toml"
            if not config_path.exists():
                raise ValidationError("No pyproject.toml found in project directory")

            # Create validation context
            context = PackageContext(
                package_name=project_dir.name,
                idea="Validation of existing project",
                output_dir=project_dir,
                config=self.config,
            )

            # Run validation pipeline
            from openpypi.stages.validation import ValidationStage

            validator = ValidationStage("validator", self.config)
            result = await validator.execute_async(context.to_dict())

            return {
                "success": result.status == StageStatus.SUCCESS,
                "validation_results": result.data,
                "message": result.message,
            }

        except Exception as e:
            logger.error(f"Project validation failed: {e}")
            return {"success": False, "error": str(e)}

    def get_supported_features(self) -> Dict[str, List[str]]:
        """Get list of supported features and integrations."""
        return {
            "frameworks": ["FastAPI", "Flask", "Django"],
            "testing": ["pytest", "unittest", "coverage"],
            "formatting": ["black", "isort", "flake8", "pylint"],
            "documentation": ["Sphinx", "MkDocs", "README"],
            "containerization": ["Docker", "docker-compose"],
            "ci_cd": ["GitHub Actions", "GitLab CI", "Jenkins"],
            "deployment": ["Heroku", "AWS", "Google Cloud", "DigitalOcean"],
            "ai_integration": ["OpenAI GPT", "Anthropic Claude", "Custom APIs"],
            "databases": ["SQLite", "PostgreSQL", "MySQL", "MongoDB"],
            "security": ["OAuth2", "JWT", "API Keys", "Rate Limiting"],
        }

    def create_fastapi_app(self, package_name: str, **kwargs) -> str:
        """Generate FastAPI application code."""
        return self.generator.create_fastapi_app(package_name, **kwargs)

    def create_docker_config(self, package_name: str, **kwargs) -> Dict[str, str]:
        """Generate Docker configuration files."""
        return self.generator.create_docker_config(package_name, **kwargs)

    def create_github_workflows(self, package_name: str, **kwargs) -> Dict[str, str]:
        """Generate GitHub Actions workflows."""
        return self.generator.create_github_workflows(package_name, **kwargs)


class CodeValidator:
    """Validates Python code quality and standards."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """Validate Python syntax."""
        try:
            compile(code, "<string>", "exec")
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {"valid": False, "errors": [f"Syntax error at line {e.lineno}: {e.msg}"]}

    def validate_imports(self, code: str) -> Dict[str, Any]:
        """Validate import statements."""
        import ast

        try:
            tree = ast.parse(code)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return {"valid": True, "imports": imports, "errors": []}

        except Exception as e:
            return {"valid": False, "imports": [], "errors": [str(e)]}

    def check_code_quality(self, code: str) -> Dict[str, Any]:
        """Check code quality metrics."""
        lines = code.split("\n")

        metrics = {
            "line_count": len(lines),
            "non_empty_lines": len([line for line in lines if line.strip()]),
            "comment_lines": len([line for line in lines if line.strip().startswith("#")]),
            "function_count": code.count("def "),
            "class_count": code.count("class "),
        }

        # Calculate comment ratio
        if metrics["non_empty_lines"] > 0:
            metrics["comment_ratio"] = metrics["comment_lines"] / metrics["non_empty_lines"]
        else:
            metrics["comment_ratio"] = 0

        return metrics


# Global instance - created when needed to avoid import-time errors
openpypi = None


def get_openpypi_instance():
    """Get or create global OpenPypi instance."""
    global openpypi
    if openpypi is None:
        openpypi = OpenPypi()
    return openpypi


async def generate_project(
    idea: str, output_dir: Union[str, Path], package_name: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for generating a complete project.

    Args:
        idea: The project idea or description
        output_dir: Directory to generate the project in
        package_name: Name for the package (auto-generated if not provided)
        **kwargs: Additional configuration options

    Returns:
        Dict containing project generation results
    """
    output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
    return await get_openpypi_instance().generate_complete_project(
        idea, output_path, package_name, **kwargs
    )


def validate_project(project_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Convenience function for validating an existing project.

    Args:
        project_dir: Path to the project directory

    Returns:
        Dict containing validation results
    """
    project_path = Path(project_dir) if isinstance(project_dir, str) else project_dir
    return asyncio.run(get_openpypi_instance().validate_project(project_path))
