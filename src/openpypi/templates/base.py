"""
Base template system for OpenPypi package generation.
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Template:
    """Represents a package template."""

    name: str
    description: str
    category: str
    author: str
    version: str = "1.0.0"
    features: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    python_version: str = ">=3.8"
    template_path: Optional[Path] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "author": self.author,
            "version": self.version,
            "features": self.features,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
            "python_version": self.python_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], template_path: Optional[Path] = None) -> "Template":
        """Create template from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            author=data["author"],
            version=data.get("version", "1.0.0"),
            features=data.get("features", []),
            dependencies=data.get("dependencies", []),
            dev_dependencies=data.get("dev_dependencies", []),
            python_version=data.get("python_version", ">=3.8"),
            template_path=template_path,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {}),
        )


class TemplateManager:
    """Manages package templates for OpenPypi."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template manager."""
        if templates_dir is None:
            # Default to package templates directory
            package_dir = Path(__file__).parent.parent
            templates_dir = package_dir / "templates"

        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize built-in templates if they don't exist
        self._initialize_builtin_templates()

    def _initialize_builtin_templates(self) -> None:
        """Initialize built-in templates."""
        builtin_templates = [
            {
                "name": "cli_tool",
                "description": "Command-line interface application with Click",
                "category": "cli",
                "author": "OpenPypi",
                "features": [
                    "Click CLI framework",
                    "Argument parsing",
                    "Configuration management",
                    "Logging setup",
                    "Progress bars",
                    "Error handling",
                ],
                "dependencies": ["click", "rich", "pyyaml"],
                "dev_dependencies": ["pytest", "pytest-cov", "black", "flake8"],
                "structure": {
                    "src/{package_name}": {
                        "__init__.py": "",
                        "__main__.py": "",
                        "cli.py": "",
                        "core.py": "",
                        "config.py": "",
                        "utils.py": "",
                    },
                    "tests": {
                        "__init__.py": "",
                        "test_cli.py": "",
                        "test_core.py": "",
                        "conftest.py": "",
                    },
                },
            },
            {
                "name": "library",
                "description": "General-purpose Python library",
                "category": "library",
                "author": "OpenPypi",
                "features": [
                    "Modular architecture",
                    "Type hints",
                    "Comprehensive documentation",
                    "Unit tests",
                    "API design",
                ],
                "dependencies": [],
                "dev_dependencies": ["pytest", "pytest-cov", "black", "flake8", "mypy"],
                "structure": {
                    "src/{package_name}": {
                        "__init__.py": "",
                        "core.py": "",
                        "utils.py": "",
                        "exceptions.py": "",
                    },
                    "tests": {
                        "__init__.py": "",
                        "test_core.py": "",
                        "test_utils.py": "",
                        "conftest.py": "",
                    },
                },
            },
            {
                "name": "web_api",
                "description": "Web API with FastAPI",
                "category": "web",
                "author": "OpenPypi",
                "features": [
                    "FastAPI framework",
                    "Async support",
                    "Pydantic models",
                    "OpenAPI documentation",
                    "Authentication",
                    "Database integration",
                ],
                "dependencies": ["fastapi", "uvicorn", "pydantic", "sqlalchemy"],
                "dev_dependencies": ["pytest", "pytest-asyncio", "httpx", "black", "flake8"],
                "structure": {
                    "src/{package_name}": {
                        "__init__.py": "",
                        "main.py": "",
                        "api": {"__init__.py": "", "routes.py": "", "dependencies.py": ""},
                        "models": {"__init__.py": "", "schemas.py": "", "database.py": ""},
                        "core": {"__init__.py": "", "config.py": "", "security.py": ""},
                    },
                    "tests": {
                        "__init__.py": "",
                        "test_api.py": "",
                        "test_models.py": "",
                        "conftest.py": "",
                    },
                },
            },
            {
                "name": "data_science",
                "description": "Data science toolkit with pandas and numpy",
                "category": "data-science",
                "author": "OpenPypi",
                "features": [
                    "Pandas integration",
                    "NumPy support",
                    "Data visualization",
                    "Statistical analysis",
                    "Jupyter notebooks",
                    "Data validation",
                ],
                "dependencies": ["pandas", "numpy", "matplotlib", "seaborn", "scipy"],
                "dev_dependencies": ["pytest", "jupyter", "black", "flake8", "mypy"],
                "structure": {
                    "src/{package_name}": {
                        "__init__.py": "",
                        "data": {
                            "__init__.py": "",
                            "loader.py": "",
                            "processor.py": "",
                            "validator.py": "",
                        },
                        "analysis": {
                            "__init__.py": "",
                            "statistics.py": "",
                            "visualization.py": "",
                        },
                        "utils": {"__init__.py": "", "helpers.py": ""},
                    },
                    "notebooks": {"examples.ipynb": "", "tutorial.ipynb": ""},
                    "tests": {
                        "__init__.py": "",
                        "test_data.py": "",
                        "test_analysis.py": "",
                        "conftest.py": "",
                    },
                },
            },
            {
                "name": "ml_toolkit",
                "description": "Machine learning toolkit with scikit-learn",
                "category": "ml",
                "author": "OpenPypi",
                "features": [
                    "Scikit-learn compatibility",
                    "Model pipelines",
                    "Feature engineering",
                    "Model evaluation",
                    "Hyperparameter tuning",
                    "Model persistence",
                ],
                "dependencies": ["scikit-learn", "pandas", "numpy", "joblib"],
                "dev_dependencies": ["pytest", "jupyter", "black", "flake8", "mypy"],
                "structure": {
                    "src/{package_name}": {
                        "__init__.py": "",
                        "models": {
                            "__init__.py": "",
                            "base.py": "",
                            "classifiers.py": "",
                            "regressors.py": "",
                        },
                        "preprocessing": {
                            "__init__.py": "",
                            "features.py": "",
                            "transformers.py": "",
                        },
                        "evaluation": {"__init__.py": "", "metrics.py": "", "validation.py": ""},
                        "utils": {"__init__.py": "", "io.py": "", "helpers.py": ""},
                    },
                    "tests": {
                        "__init__.py": "",
                        "test_models.py": "",
                        "test_preprocessing.py": "",
                        "test_evaluation.py": "",
                        "conftest.py": "",
                    },
                },
            },
        ]

        for template_data in builtin_templates:
            template_dir = self.templates_dir / template_data["name"]
            if not template_dir.exists():
                self._create_template_directory(template_data, template_dir)

    def _create_template_directory(self, template_data: Dict[str, Any], template_dir: Path) -> None:
        """Create a template directory structure."""
        template_dir.mkdir(parents=True, exist_ok=True)

        # Save template metadata
        metadata_file = template_dir / "template.yaml"
        with open(metadata_file, "w") as f:
            yaml.dump(template_data, f, default_flow_style=False)

        # Create directory structure if specified
        structure = template_data.get("structure", {})
        if structure:
            self._create_directory_structure(template_dir, structure)

        logger.info(f"Created built-in template: {template_data['name']}")

    def _create_directory_structure(self, base_dir: Path, structure: Dict[str, Any]) -> None:
        """Recursively create directory structure."""
        for name, content in structure.items():
            path = base_dir / name

            if isinstance(content, dict):
                # It's a directory
                path.mkdir(parents=True, exist_ok=True)
                self._create_directory_structure(path, content)
            else:
                # It's a file
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    path.write_text(content or "# Module implementation\n")

    async def list_templates(self) -> List[Template]:
        """List all available templates."""
        templates = []

        for template_dir in self.templates_dir.iterdir():
            if template_dir.is_dir():
                template = await self._load_template(template_dir)
                if template:
                    templates.append(template)

        return sorted(templates, key=lambda t: t.name)

    async def _load_template(self, template_dir: Path) -> Optional[Template]:
        """Load a template from directory."""
        try:
            metadata_file = template_dir / "template.yaml"
            if not metadata_file.exists():
                # Try JSON format as fallback
                metadata_file = template_dir / "template.json"
                if not metadata_file.exists():
                    logger.warning(f"No metadata file found in template: {template_dir}")
                    return None

            # Load metadata
            if metadata_file.suffix == ".yaml":
                with open(metadata_file, "r") as f:
                    data = yaml.safe_load(f)
            else:
                with open(metadata_file, "r") as f:
                    data = json.load(f)

            # Create template instance
            template = Template.from_dict(data, template_path=template_dir)
            return template

        except Exception as e:
            logger.error(f"Failed to load template from {template_dir}: {e}")
            return None

    async def get_template(self, name: str) -> Optional[Template]:
        """Get a specific template by name."""
        template_dir = self.templates_dir / name
        if template_dir.exists():
            return await self._load_template(template_dir)
        return None

    async def create_template(
        self,
        name: str,
        description: str,
        category: str,
        features: List[str],
        author: str = "User",
        dependencies: Optional[List[str]] = None,
        dev_dependencies: Optional[List[str]] = None,
        python_version: str = ">=3.8",
        structure: Optional[Dict[str, Any]] = None,
        **metadata,
    ) -> Path:
        """
        Create a new template.

        Args:
            name: Template name
            description: Template description
            category: Template category
            features: List of features
            author: Template author
            dependencies: Runtime dependencies
            dev_dependencies: Development dependencies
            python_version: Python version requirement
            structure: Directory structure definition
            **metadata: Additional metadata

        Returns:
            Path to created template directory
        """
        template_dir = self.templates_dir / name

        if template_dir.exists():
            raise TemplateError(f"Template '{name}' already exists")

        # Create template data
        template_data = {
            "name": name,
            "description": description,
            "category": category,
            "author": author,
            "version": "1.0.0",
            "features": features,
            "dependencies": dependencies or [],
            "dev_dependencies": dev_dependencies or [],
            "python_version": python_version,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata,
        }

        if structure:
            template_data["structure"] = structure

        # Create template directory
        self._create_template_directory(template_data, template_dir)

        logger.info(f"Created template: {name}")
        return template_dir

    async def update_template(self, name: str, **updates) -> bool:
        """
        Update an existing template.

        Args:
            name: Template name
            **updates: Fields to update

        Returns:
            bool: True if updated successfully
        """
        template = await self.get_template(name)
        if not template:
            raise TemplateError(f"Template '{name}' not found")

        # Load current metadata
        metadata_file = template.template_path / "template.yaml"
        with open(metadata_file, "r") as f:
            data = yaml.safe_load(f)

        # Apply updates
        data.update(updates)
        data["updated_at"] = datetime.now().isoformat()

        # Save updated metadata
        with open(metadata_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        logger.info(f"Updated template: {name}")
        return True

    async def delete_template(self, name: str) -> bool:
        """
        Delete a template.

        Args:
            name: Template name

        Returns:
            bool: True if deleted successfully
        """
        template_dir = self.templates_dir / name

        if not template_dir.exists():
            raise TemplateError(f"Template '{name}' not found")

        # Don't allow deletion of built-in templates
        template = await self.get_template(name)
        if template and template.author == "OpenPypi":
            raise TemplateError(f"Cannot delete built-in template: {name}")

        # Delete template directory
        shutil.rmtree(template_dir)

        logger.info(f"Deleted template: {name}")
        return True

    async def apply_template(
        self, template_name: str, target_dir: Path, package_name: str, **substitutions
    ) -> Dict[str, Any]:
        """
        Apply a template to create package structure.

        Args:
            template_name: Name of template to apply
            target_dir: Target directory for package
            package_name: Name of the package
            **substitutions: Variable substitutions

        Returns:
            Dict containing application results
        """
        template = await self.get_template(template_name)
        if not template:
            raise TemplateError(f"Template '{template_name}' not found")

        logger.info(f"Applying template '{template_name}' to {target_dir}")

        # Prepare substitutions
        substitutions.update(
            {
                "package_name": package_name,
                "template_name": template_name,
                "author": substitutions.get("author", "Unknown"),
                "email": substitutions.get("email", "nikjois@llamasearch.ai"),
                "description": substitutions.get(
                    "description", f"A Python package generated from {template_name} template"
                ),
                "version": substitutions.get("version", "0.1.0"),
                "license": substitutions.get("license", "MIT"),
                "python_version": template.python_version,
            }
        )

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy template files
        files_created = []
        if template.template_path:
            files_created = await self._copy_template_files(
                template.template_path, target_dir, substitutions
            )

        # Generate pyproject.toml
        pyproject_path = target_dir / "pyproject.toml"
        await self._generate_pyproject_toml(template, pyproject_path, substitutions)
        files_created.append(str(pyproject_path))

        # Generate README.md
        readme_path = target_dir / "README.md"
        await self._generate_readme(template, readme_path, substitutions)
        files_created.append(str(readme_path))

        result = {
            "template_applied": template_name,
            "target_directory": str(target_dir),
            "package_name": package_name,
            "files_created": files_created,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "features": template.features,
        }

        logger.info(f"Template '{template_name}' applied successfully")
        return result

    async def _copy_template_files(
        self, template_dir: Path, target_dir: Path, substitutions: Dict[str, str]
    ) -> List[str]:
        """Copy template files with substitutions."""
        files_created = []

        # Skip metadata files
        skip_files = {"template.yaml", "template.json", ".git"}

        for item in template_dir.rglob("*"):
            if item.name in skip_files or item.is_dir():
                continue

            # Calculate relative path
            rel_path = item.relative_to(template_dir)

            # Apply substitutions to path
            target_path_str = str(rel_path)
            for key, value in substitutions.items():
                target_path_str = target_path_str.replace(f"{{{key}}}", value)

            target_path = target_dir / target_path_str
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Read and process file content
            try:
                content = item.read_text(encoding="utf-8")

                # Apply substitutions to content
                for key, value in substitutions.items():
                    content = content.replace(f"{{{key}}}", value)

                # Write processed content
                target_path.write_text(content, encoding="utf-8")
                files_created.append(str(target_path))

            except UnicodeDecodeError:
                # Binary file, copy as-is
                shutil.copy2(item, target_path)
                files_created.append(str(target_path))

        return files_created

    async def _generate_pyproject_toml(
        self, template: Template, output_path: Path, substitutions: Dict[str, str]
    ) -> None:
        """Generate pyproject.toml file."""
        content = f"""[build-system]
requires = ["setuptools>=69.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{substitutions['package_name']}"
version = "{substitutions['version']}"
description = "{substitutions['description']}"
readme = "README.md"
requires-python = "{template.python_version}"
license = {{text = "{substitutions['license']}"}}
authors = [
    {{name = "{substitutions['author']}", email = "{substitutions['email']}"}},
]
keywords = {template.features[:5]}
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = {template.dependencies}

[project.optional-dependencies]
dev = {template.dev_dependencies + ["pytest", "pytest-cov", "black", "flake8"]}

[tool.setuptools]
packages = ["{substitutions['package_name']}"]
package-dir = {{"" = "src"}}

[project.urls]
Homepage = "https://github.com/{substitutions['author']}/{substitutions['package_name']}"
Repository = "https://github.com/{substitutions['author']}/{substitutions['package_name']}"
Issues = "https://github.com/{substitutions['author']}/{substitutions['package_name']}/issues"
"""

        # Add entry points for CLI templates
        if template.category == "cli":
            content += f"""
[project.scripts]
{substitutions['package_name']} = "{substitutions['package_name']}.cli:main"
"""

        output_path.write_text(content)

    async def _generate_readme(
        self, template: Template, output_path: Path, substitutions: Dict[str, str]
    ) -> None:
        """Generate README.md file."""
        content = f"""# {substitutions['package_name']}

{substitutions['description']}

## Features

{chr(10).join(f"- {feature}" for feature in template.features)}

## Installation

```bash
pip install {substitutions['package_name']}
```

## Usage

```python
import {substitutions['package_name']}

# Your code here
```

## Development

1. Clone the repository:
```bash
git clone https://github.com/{substitutions['author']}/{substitutions['package_name']}.git
cd {substitutions['package_name']}
```

2. Install development dependencies:
```bash
pip install -e .[dev]
```

3. Run tests:
```bash
pytest
```

## License

{substitutions['license']} License
"""

        output_path.write_text(content)


class TemplateError(Exception):
    """Exception raised for template-related errors."""

    pass
