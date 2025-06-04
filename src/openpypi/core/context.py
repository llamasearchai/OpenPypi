"""
Package context management for maintaining state across stages.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.logger import get_logger
from .config import Config

logger = get_logger(__name__)


@dataclass
class PackageContext:
    """
    Context object that maintains state throughout package creation.

    This class stores all information needed across the 7 stages of
    package generation, including user inputs, AI responses, and
    generated artifacts.
    """

    # User inputs
    idea: str
    output_dir: Path
    author: str = "OpenPypi User"
    email: str = "nikjois@llamasearch.ai"
    license_type: str = "MIT"
    python_version: str = ">=3.8"
    package_type: str = "library"
    features: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    template: Optional[str] = None

    # Generated metadata
    package_name: str = ""
    version: str = "0.1.0"
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)

    # Stage outputs
    stage_outputs: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Generate package name if not set
        if not self.package_name:
            self.package_name = self._generate_package_name()

    def _generate_package_name(self) -> str:
        """Generate package name from idea."""
        words = self.idea.lower().split()
        stop_words = {"a", "an", "the", "for", "with", "to", "and", "or", "but"}
        meaningful_words = [w for w in words if w not in stop_words and w.isalpha()]

        if not meaningful_words:
            return "ai_package"

        package_name = "_".join(meaningful_words[:2])
        # Clean the name
        package_name = "".join(c if c.isalnum() or c == "_" else "_" for c in package_name)
        package_name = package_name.strip("_").lower()

        return package_name or "ai_package"

    def set_stage_output(self, stage: str, output: Any) -> None:
        """Set output for a specific stage."""
        self.stage_outputs[stage] = output

    def get_stage_output(self, stage: str) -> Any:
        """Get output from a specific stage."""
        return self.stage_outputs.get(stage)

    def add_dependency(self, dependency: str, dev: bool = False) -> None:
        """Add a dependency to the package."""
        if dev:
            if dependency not in self.dev_dependencies:
                self.dev_dependencies.append(dependency)
        else:
            if dependency not in self.dependencies:
                self.dependencies.append(dependency)

    def add_feature(self, feature: str) -> None:
        """Add a feature to the package."""
        if feature not in self.features:
            self.features.append(feature)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        data = asdict(self)
        # Convert Path to string
        data["output_dir"] = str(self.output_dir)
        data["created_at"] = self.created_at.isoformat()
        return data

    def save(self, filepath: Optional[Path] = None) -> None:
        """Save context to JSON file."""
        if filepath is None:
            filepath = self.output_dir / ".openpypi_context.json"

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "PackageContext":
        """Load context from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        # Convert string back to Path
        data["output_dir"] = Path(data["output_dir"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])

        return cls(**data)

    def get_package_dir(self) -> Path:
        """Get the main package source directory."""
        return self.output_dir / "src" / self.package_name

    def get_tests_dir(self) -> Path:
        """Get the tests directory."""
        return self.output_dir / "tests"

    def get_docs_dir(self) -> Path:
        """Get the documentation directory."""
        return self.output_dir / "docs"


class Context:
    """General-purpose context for storing arbitrary data."""

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initialize context with optional initial data."""
        self.data: Dict[str, Any] = initial_data.copy() if initial_data else {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value by key."""
        self.data[key] = value

    def has(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data

    def remove(self, key: str) -> None:
        """Remove key from context."""
        self.data.pop(key, None)

    def update(self, data: Optional[Dict[str, Any]]) -> None:
        """Update context with dictionary data."""
        if data:
            self.data.update(data)

    def clear(self) -> None:
        """Clear all data."""
        self.data.clear()

    def get_all(self) -> Dict[str, Any]:
        """Get copy of all data."""
        return self.data.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        """Create context from dictionary."""
        return cls(data)

    def merge(self, other: "Context") -> "Context":
        """Merge with another context and return new context."""
        merged_data = self.data.copy()
        merged_data.update(other.data)
        return Context(merged_data)

    def copy(self) -> "Context":
        """Create a copy of this context."""
        return Context(self.data)


class ContextManager:
    """Manager for context operations."""

    def __init__(self, context: Optional[Context] = None):
        """Initialize context manager."""
        self.context = context or Context()

    def create_project_context(self, config: Config, output_dir: Union[str, Path]) -> Context:
        """Create project context from config and output directory."""
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        # Create context with project information
        project_context = Context(
            {
                "project_config": config,
                "output_dir": output_dir,
                "project_name": config.project_name,
                "package_name": config.package_name,
                "author": config.author,
                "email": config.email,
                "version": config.version,
                "description": config.description,
                "use_git": config.use_git,
                "use_docker": config.use_docker,
                "use_fastapi": config.use_fastapi,
                "create_tests": config.create_tests,
                "test_framework": config.test_framework,
            }
        )

        self.context = project_context
        return project_context

    def add_stage_result(self, stage_name: str, result: Any) -> None:
        """Add stage result to context."""
        self.context.set(f"{stage_name}_result", result)

    def get_stage_result(self, stage_name: str) -> Any:
        """Get stage result from context."""
        return self.context.get(f"{stage_name}_result")

    def update_from_config(self, config: Config) -> None:
        """Update context from config object."""
        config_dict = config.to_dict()
        self.context.update(config_dict)

    def set_paths(self, paths: Dict[str, Path]) -> None:
        """Set path information in context."""
        self.context.update(paths)

    def validate_context(self) -> bool:
        """Validate that context has required fields."""
        required_fields = ["project_config", "output_dir"]
        return all(self.context.has(field) for field in required_fields)

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of context information."""
        project_config = self.context.get("project_config")

        # Try to get values from context first, then from project_config as fallback
        summary = {
            "project_name": self.context.get("project_name")
            or (getattr(project_config, "project_name", None) if project_config else None),
            "package_name": self.context.get("package_name")
            or (getattr(project_config, "package_name", None) if project_config else None),
            "version": self.context.get("version")
            or (getattr(project_config, "version", None) if project_config else None),
            "output_dir": str(self.context.get("output_dir", "")),
            "author": self.context.get("author")
            or (getattr(project_config, "author", None) if project_config else None),
            "email": self.context.get("email")
            or (getattr(project_config, "email", None) if project_config else None),
        }

        if project_config:
            summary.update(
                {
                    "use_git": getattr(project_config, "use_git", False),
                    "use_docker": getattr(project_config, "use_docker", False),
                    "use_fastapi": getattr(project_config, "use_fastapi", False),
                    "create_tests": getattr(project_config, "create_tests", False),
                }
            )

        return summary

    def reset(self) -> None:
        """Reset context to empty state."""
        self.context.clear()
