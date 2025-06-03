"""
Main project generator for OpenPypi.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.formatters import ConfigFormatter
from ..utils.formatters import ProjectGenerator as BaseProjectGenerator
from ..utils.logger import get_logger
from .config import Config
from .exceptions import GenerationError

logger = get_logger(__name__)


class ProjectGenerator:
    """Main project generator that creates complete Python projects."""

    def __init__(self, config: Config):
        self.config = config
        self.base_generator = BaseProjectGenerator()
        self.config_formatter = ConfigFormatter()
        self.project_name = config.project_name
        self.package_name = config.package_name
        self.templates_dir = Path(__file__).parent.parent / "templates"

    def generate(self) -> Dict[str, Any]:
        """Generate a complete Python project."""
        try:
            # Validate configuration
            self.config.validate()

            # Create project directory
            project_dir = self.config.output_dir / self.config.project_name
            project_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Generating project in {project_dir}")

            results = {
                "project_dir": str(project_dir),
                "files_created": [],
                "directories_created": [],
                "commands_run": [],
                "warnings": [],
            }

            # Generate basic project structure
            structure_results = self._create_project_structure(project_dir)
            self._merge_results(results, structure_results)

            # Generate configuration files
            config_results = self._create_config_files(project_dir)
            self._merge_results(results, config_results)

            # Generate source code
            source_results = self._create_source_code(project_dir)
            self._merge_results(results, source_results)

            # Generate tests
            if self.config.create_tests:
                test_results = self._create_tests(project_dir)
                self._merge_results(results, test_results)

            # Generate documentation
            docs_results = self._create_documentation(project_dir)
            self._merge_results(results, docs_results)

            # Generate Docker files
            if self.config.use_docker:
                docker_results = self._create_docker_files(project_dir)
                self._merge_results(results, docker_results)

            # Generate CI/CD files
            if self.config.use_github_actions:
                ci_results = self._create_ci_files(project_dir)
                self._merge_results(results, ci_results)

            # Initialize git repository
            if self.config.use_git:
                git_results = self._initialize_git(project_dir)
                self._merge_results(results, git_results)

            # Install dependencies
            install_results = self._install_dependencies(project_dir)
            self._merge_results(results, install_results)

            logger.info("Project generation completed successfully")
            return results

        except Exception as e:
            logger.error(f"Project generation failed: {e}")
            raise GenerationError(f"Failed to generate project: {e}")

    def _create_project_structure(self, project_dir: Path) -> Dict[str, Any]:
        """Create basic project directory structure."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # Create directories
        directories = [
            Path("src") / self.config.package_name,
            Path("tests"),
            Path("docs"),
            Path("scripts"),
            Path("data"),
            Path("configs"),
        ]

        if self.config.use_fastapi:
            directories.extend(
                [
                    Path("src") / self.config.package_name / "api",
                    Path("src") / self.config.package_name / "models",
                    Path("src") / self.config.package_name / "services",
                ]
            )

        for directory in directories:
            full_path = project_dir / directory
            full_path.mkdir(parents=True, exist_ok=True)
            results["directories_created"].append(str(directory))

        # Create __init__.py files
        init_files = [
            Path("src") / self.config.package_name / "__init__.py",
            Path("tests") / "__init__.py",
        ]

        if self.config.use_fastapi:
            init_files.extend(
                [
                    Path("src") / self.config.package_name / "api" / "__init__.py",
                    Path("src") / self.config.package_name / "models" / "__init__.py",
                    Path("src") / self.config.package_name / "services" / "__init__.py",
                ]
            )

        for init_file in init_files:
            full_path = project_dir / init_file
            full_path.write_text('"""Package initialization."""\n')
            results["files_created"].append(str(init_file))

        return results

    def _create_config_files(self, project_dir: Path) -> Dict[str, Any]:
        """Create configuration files."""
        metadata = {
            "author": self.config.author,
            "email": self.config.email,
            "description": self.config.description,
            "license": self.config.license,
            "python_requires": self.config.python_requires,
            "dependencies": self._get_dependencies(),
            "python_versions": ["3.8", "3.9", "3.10", "3.11", "3.12"],
        }

        # Generate pyproject.toml
        results = self.config_formatter.generate_config_files(
            project_dir, self.config.package_name, metadata, ["toml"]
        )

        # Create requirements files
        self._create_requirements_files(project_dir, results)

        # Create .gitignore
        gitignore_content = self.base_generator._generate_gitignore(
            self.config.package_name, metadata
        )
        gitignore_path = project_dir / ".gitignore"
        gitignore_path.write_text(gitignore_content)
        results["files_created"].append(".gitignore")

        return results

    def _create_source_code(self, project_dir: Path) -> Dict[str, Any]:
        """Create source code files."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # Main module
        main_module_content = self._generate_main_module()
        main_module_path = project_dir / "src" / self.config.package_name / "main.py"
        main_module_path.write_text(main_module_content)
        results["files_created"].append(f"src/{self.config.package_name}/main.py")

        # CLI module
        cli_module_content = self._generate_cli_module()
        cli_module_path = project_dir / "src" / self.config.package_name / "cli.py"
        cli_module_path.write_text(cli_module_content)
        results["files_created"].append(f"src/{self.config.package_name}/cli.py")

        # Utils module
        utils_module_content = self._generate_utils_module()
        utils_module_path = project_dir / "src" / self.config.package_name / "utils.py"
        utils_module_path.write_text(utils_module_content)
        results["files_created"].append(f"src/{self.config.package_name}/utils.py")

        # FastAPI app
        if self.config.use_fastapi:
            fastapi_results = self._create_fastapi_app(project_dir)
            self._merge_results(results, fastapi_results)

        # OpenAI integration
        if self.config.use_openai:
            openai_results = self._create_openai_integration(project_dir)
            self._merge_results(results, openai_results)

        return results

    def _create_tests(self, project_dir: Path) -> Dict[str, Any]:
        """Create test files."""
        modules = ["main", "utils", "cli"]
        if self.config.use_fastapi:
            modules.extend(["api", "models", "services"])
        if self.config.use_openai:
            modules.append("openai_client")

        return self.base_generator._generate_tests(
            project_dir, self.config.package_name, modules, self.config.test_framework
        )

    def _create_documentation(self, project_dir: Path) -> Dict[str, Any]:
        """Create documentation files."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # README.md
        readme_content = self._generate_readme()
        readme_path = project_dir / "README.md"
        readme_path.write_text(readme_content)
        results["files_created"].append("README.md")

        # CHANGELOG.md
        changelog_content = self._generate_changelog()
        changelog_path = project_dir / "CHANGELOG.md"
        changelog_path.write_text(changelog_content)
        results["files_created"].append("CHANGELOG.md")

        # LICENSE
        license_content = self._generate_license()
        license_path = project_dir / "LICENSE"
        license_path.write_text(license_content)
        results["files_created"].append("LICENSE")

        return results

    def _create_docker_files(self, project_dir: Path) -> Dict[str, Any]:
        """Create Docker-related files."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # Dockerfile
        dockerfile_content = self._generate_dockerfile()
        dockerfile_path = project_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        results["files_created"].append("Dockerfile")

        # docker-compose.yml
        compose_content = self._generate_docker_compose()
        compose_path = project_dir / "docker-compose.yml"
        compose_path.write_text(compose_content)
        results["files_created"].append("docker-compose.yml")

        # .dockerignore
        dockerignore_content = self._generate_dockerignore()
        dockerignore_path = project_dir / ".dockerignore"
        dockerignore_path.write_text(dockerignore_content)
        results["files_created"].append(".dockerignore")

        return results

    def _create_ci_files(self, project_dir: Path) -> Dict[str, Any]:
        """Create CI/CD configuration files."""
        # Create GitHub Actions workflow
        workflows_dir = project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = self._generate_github_workflow()
        workflow_path = workflows_dir / "ci.yml"
        workflow_path.write_text(workflow_content)

        return {
            "files_created": [".github/workflows/ci.yml"],
            "directories_created": [".github/workflows"],
            "warnings": [],
        }

    def _initialize_git(self, project_dir: Path) -> Dict[str, Any]:
        """Initialize git repository."""
        results = {
            "files_created": [],
            "directories_created": [],
            "commands_run": [],
            "warnings": [],
        }

        try:
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
            results["commands_run"].append("git init")

            # Add all files
            subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
            results["commands_run"].append("git add .")

            # Initial commit
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )
            results["commands_run"].append('git commit -m "Initial commit"')

        except subprocess.CalledProcessError as e:
            results["warnings"].append(f"Git initialization failed: {e}")
        except FileNotFoundError:
            results["warnings"].append("Git not found - skipping git initialization")

        return results

    def _install_dependencies(self, project_dir: Path) -> Dict[str, Any]:
        """Install project dependencies."""
        results = {
            "files_created": [],
            "directories_created": [],
            "commands_run": [],
            "warnings": [],
        }

        try:
            # Create virtual environment
            subprocess.run(
                ["python", "-m", "venv", "venv"], cwd=project_dir, check=True, capture_output=True
            )
            results["commands_run"].append("python -m venv venv")

            # Install in development mode
            pip_cmd = str(project_dir / "venv" / "bin" / "pip")
            if not Path(pip_cmd).exists():
                pip_cmd = str(project_dir / "venv" / "Scripts" / "pip.exe")  # Windows

            subprocess.run(
                [pip_cmd, "install", "-e", ".[dev]"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )
            results["commands_run"].append("pip install -e .[dev]")

        except subprocess.CalledProcessError as e:
            results["warnings"].append(f"Dependency installation failed: {e}")
        except FileNotFoundError:
            results["warnings"].append("Python not found - skipping dependency installation")

        return results

    def _get_dependencies(self) -> List[str]:
        """Get list of dependencies based on configuration."""
        deps = list(self.config.dependencies)

        if self.config.use_fastapi:
            deps.extend(["fastapi>=0.104.0", "uvicorn>=0.24.0"])

        if self.config.use_openai:
            deps.append("openai>=1.0.0")

        return deps

    def _merge_results(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Merge results from sub-operations."""
        for key in ["files_created", "directories_created", "commands_run", "warnings"]:
            if key in source:
                target[key].extend(source[key])

    # Content generation methods
    def _generate_main_module(self) -> str:
        """Generate main module content."""
        return f'''"""
Main module for {self.config.package_name}.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class {self.config.package_name.title().replace('_', '')}:
    """Main class for {self.config.package_name}."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the main class."""
        self.config = config or {{}}
        logger.info("Initialized {self.config.package_name}")
    
    def run(self) -> Dict[str, Any]:
        """Run the main functionality."""
        logger.info("Running main functionality")
        
        result = {{
            "status": "success",
            "message": "Main functionality executed successfully",
            "data": {{}}
        }}
        
        return result
    
    def process_data(self, data: Any) -> Any:
        """Process input data."""
        logger.info("Processing data")
        
        # Add your data processing logic here
        processed_data = data
        
        return processed_data


def main() -> None:
    """Main entry point."""
    app = {self.config.package_name.title().replace('_', '')}()
    result = app.run()
    print(f"Result: {{result}}")


if __name__ == "__main__":
    main()
'''

    def _generate_cli_module(self) -> str:
        """Generate CLI module content."""
        return f'''"""
Command-line interface for {self.config.package_name}.
"""

import argparse
import sys
from typing import List, Optional

from .main import {self.config.package_name.title().replace('_', '')}


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="{self.config.description}",
        prog="{self.config.package_name}"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"{{parser.prog}} {self.config.version}"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the main functionality")
    run_parser.add_argument(
        "--data",
        type=str,
        help="Input data to process"
    )
    
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    try:
        # Configure logging
        import logging
        level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
        
        # Load configuration
        config = {{}}
        if args.config:
            # Add configuration loading logic here
            pass
        
        # Initialize main application
        app = {self.config.package_name.title().replace('_', '')}(config)
        
        # Execute command
        if args.command == "run":
            result = app.run()
            print(f"Result: {{result}}")
            return 0
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''

    def _generate_utils_module(self) -> str:
        """Generate utils module content."""
        return f'''"""
Utility functions for {self.config.package_name}.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON file {{file_path}}: {{e}}")
        raise


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """Save data to JSON file."""
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved data to {{file_path}}")
    except Exception as e:
        logger.error(f"Failed to save JSON file {{file_path}}: {{e}}")
        raise


def validate_input(data: Any, required_fields: Optional[list] = None) -> bool:
    """Validate input data."""
    if not isinstance(data, dict):
        return False
    
    if required_fields:
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {{field}}")
                return False
    
    return True


def format_response(
    status: str,
    message: str,
    data: Optional[Any] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """Format standardized response."""
    response = {{
        "status": status,
        "message": message
    }}
    
    if data is not None:
        response["data"] = data
    
    if error:
        response["error"] = error
    
    return response


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
'''

    def _create_requirements_files(self, project_dir: Path, results: Dict[str, Any]) -> None:
        """Create requirements files."""
        # requirements.txt
        deps = self._get_dependencies()
        requirements_content = "\n".join(deps) + "\n"
        requirements_path = project_dir / "requirements.txt"
        requirements_path.write_text(requirements_content)
        results["files_created"].append("requirements.txt")

        # requirements-dev.txt
        dev_deps = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "pylint>=2.17.0",
            "mypy>=1.4.0",
        ]
        dev_deps.extend(self.config.dev_dependencies)
        dev_requirements_content = "-r requirements.txt\n" + "\n".join(dev_deps) + "\n"
        dev_requirements_path = project_dir / "requirements-dev.txt"
        dev_requirements_path.write_text(dev_requirements_content)
        results["files_created"].append("requirements-dev.txt")

    def _create_fastapi_app(self, project_dir: Path) -> Dict[str, Any]:
        """Create FastAPI application files."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # Main FastAPI app
        app_content = self._generate_fastapi_app()
        app_path = project_dir / "src" / self.config.package_name / "api" / "app.py"
        app_path.write_text(app_content)
        results["files_created"].append(f"src/{self.config.package_name}/api/app.py")

        # API routes
        routes_content = self._generate_api_routes()
        routes_path = project_dir / "src" / self.config.package_name / "api" / "routes.py"
        routes_path.write_text(routes_content)
        results["files_created"].append(f"src/{self.config.package_name}/api/routes.py")

        # Pydantic models
        models_content = self._generate_pydantic_models()
        models_path = project_dir / "src" / self.config.package_name / "models" / "schemas.py"
        models_path.write_text(models_content)
        results["files_created"].append(f"src/{self.config.package_name}/models/schemas.py")

        return results

    def _create_openai_integration(self, project_dir: Path) -> Dict[str, Any]:
        """Create OpenAI integration files."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # OpenAI client
        client_content = self._generate_openai_client()
        client_path = (
            project_dir / "src" / self.config.package_name / "services" / "openai_client.py"
        )
        client_path.write_text(client_content)
        results["files_created"].append(f"src/{self.config.package_name}/services/openai_client.py")

        return results

    # Additional content generation methods would continue here...
    # For brevity, I'll include key methods

    def _generate_fastapi_app(self) -> str:
        """Generate FastAPI application code."""
        return f'''"""
FastAPI application for {self.config.package_name}.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes import router
from ..main import {self.config.package_name.title().replace('_', '')}

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="{self.config.project_name}",
    description="{self.config.description}",
    version="{self.config.version}"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

# Initialize main application
main_app = {self.config.package_name.title().replace('_', '')}()


@app.get("/")
async def root():
    """Root endpoint."""
    return {{"message": "Welcome to {self.config.project_name} API"}}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy", "service": "{self.config.package_name}"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    def _generate_fastapi_section(self) -> str:
        """Generate FastAPI section for README."""
        return f"""
Start the FastAPI server:

```bash
uvicorn {self.config.package_name}.api.app:app --reload
```

Visit http://localhost:8000/docs for the interactive API documentation.
"""

    def _generate_readme(self) -> str:
        """Generate README.md content."""
        return f"""# {self.config.project_name}

{self.config.description}

## Features

- Python {self.config.python_requires.replace('>=', '')}+ support
{"- FastAPI web framework" if self.config.use_fastapi else ""}
{"- OpenAI integration" if self.config.use_openai else ""}
{"- Docker support" if self.config.use_docker else ""}
{"- Comprehensive test suite" if self.config.create_tests else ""}
- Automated CI/CD with GitHub Actions
- Code formatting with Black and isort
- Type checking with mypy
- Linting with flake8 and pylint

## Installation

```bash
pip install {self.config.package_name}
```

## Quick Start

```python
from {self.config.package_name} import {self.config.package_name.title().replace('_', '')}

# Initialize the application
app = {self.config.package_name.title().replace('_', '')}()

# Run main functionality
result = app.run()
print(result)
```

## CLI Usage

```bash
# Run the application
{self.config.package_name} run

# Show help
{self.config.package_name} --help
```

{"## API Usage" if self.config.use_fastapi else ""}
{self._generate_fastapi_section() if self.config.use_fastapi else ""}

## Development

### Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\\Scripts\\activate` (Windows)
4. Install dependencies: `pip install -e .[dev]`

### Testing

```bash
pytest
```

### Code Formatting

```bash
black src tests
isort src tests
```

### Linting

```bash
flake8 src tests
pylint src
mypy src
```

## License

This project is licensed under the {self.config.license} License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Author

{self.config.author} <{self.config.email}>
"""

    def _get_backslash_continuation(self) -> str:
        """Get backslash for shell continuation."""
        return "\\"

    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile content."""
        backslash = self._get_backslash_continuation()
        expose_port = "EXPOSE 8000" if self.config.use_fastapi else ""

        if self.config.use_fastapi:
            cmd = f'CMD ["uvicorn", "{self.config.package_name}.api.app:app", "--host", "0.0.0.0", "--port", "8000"]'
        else:
            cmd = f'CMD ["{self.config.package_name}", "run"]'

        return f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y {backslash}
    build-essential {backslash}
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port for FastAPI
{expose_port}

# Set the default command
{cmd}
"""

    def _generate_github_workflow(self) -> str:
        """Generate GitHub Actions workflow."""
        return f"""name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Lint with flake8
      run: |
        flake8 src tests
    
    - name: Test with pytest
      run: |
        pytest --cov={self.config.package_name} --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
"""

    # Additional methods for generating other files...
    def _generate_changelog(self) -> str:
        """Generate CHANGELOG.md content."""
        return f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
{"- FastAPI web framework integration" if self.config.use_fastapi else ""}
{"- OpenAI API integration" if self.config.use_openai else ""}
{"- Docker support" if self.config.use_docker else ""}
{"- Comprehensive test suite" if self.config.create_tests else ""}
- CI/CD with GitHub Actions
- Code formatting and linting setup

## [{self.config.version}] - 2024-01-01

### Added
- Initial release
"""

    def _generate_license(self) -> str:
        """Generate LICENSE file content."""
        if self.config.license.upper() == "MIT":
            return f"""MIT License

Copyright (c) 2024 {self.config.author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        else:
            return f"# {self.config.license} License\n\nSee {self.config.license} license terms."

    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml content."""
        if self.config.use_fastapi:
            return f"""version: '3.8'

services:
  {self.config.package_name}:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
    restart: unless-stopped
"""
        else:
            return f"""version: '3.8'

services:
  {self.config.package_name}:
    build: .
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
    restart: unless-stopped
"""

    def _generate_dockerignore(self) -> str:
        """Generate .dockerignore content."""
        return """.git
.gitignore
README.md
CHANGELOG.md
.pytest_cache
.coverage
htmlcov/
.tox
.mypy_cache
.vscode
.idea
*.egg-info
dist/
build/
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv/
.env
.DS_Store
Thumbs.db
"""

    def _generate_api_routes(self) -> str:
        """Generate API routes for FastAPI."""
        return f'''"""
API routes for {self.config.package_name}.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ..models.schemas import ProcessRequest, ProcessResponse
from ..main import {self.config.package_name.title().replace('_', '')}

router = APIRouter()

# Initialize main application
main_app = {self.config.package_name.title().replace('_', '')}()


@router.post("/process", response_model=ProcessResponse)
async def process_data(request: ProcessRequest) -> ProcessResponse:
    """Process data endpoint."""
    try:
        result = main_app.process_data(request.data)
        return ProcessResponse(
            status="success",
            message="Data processed successfully",
            result=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get application status."""
    return {{
        "status": "running",
        "service": "{self.config.package_name}",
        "version": "{self.config.version}"
    }}
'''

    def _generate_pydantic_models(self) -> str:
        """Generate Pydantic models for FastAPI."""
        return '''"""
Pydantic models for API schemas.
"""

from pydantic import BaseModel
from typing import Any, Optional


class ProcessRequest(BaseModel):
    """Request model for data processing."""
    data: Any
    options: Optional[dict] = None


class ProcessResponse(BaseModel):
    """Response model for data processing."""
    status: str
    message: str
    result: Any
    error: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str
    service: str
    version: str
'''

    def _generate_openai_client(self) -> str:
        """Generate OpenAI client integration."""
        return f'''"""
OpenAI API client for {self.config.package_name}.
"""

import os
import logging
from typing import Dict, List, Optional, Any

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("OpenAI package not installed. Install with: pip install openai")

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI API client wrapper."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info("OpenAI client initialized")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a chat completion."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {{
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }}
            
        except Exception as e:
            logger.error(f"Chat completion failed: {{e}}")
            raise
    
    async def text_completion(
        self,
        prompt: str,
        model: str = "text-davinci-003",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a text completion."""
        try:
            response = self.client.completions.create(
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {{
                "text": response.choices[0].text,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }}
            
        except Exception as e:
            logger.error(f"Text completion failed: {{e}}")
            raise
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002"
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {{e}}")
            raise
'''

    # Test compatibility methods
    def generate_project_structure(self, output_dir: Path) -> Dict[str, Any]:
        """Generate basic project structure (test compatibility method)."""
        try:
            structure_results = self._create_project_structure(output_dir)
            return {"success": True, **structure_results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_package_structure(self, output_dir: Path) -> Dict[str, Any]:
        """Create package structure (test compatibility method)."""
        return self.generate_project_structure(output_dir)

    def create_configuration_files(self, output_dir: Path) -> Dict[str, Any]:
        """Create configuration files (test compatibility method)."""
        try:
            config_results = self._create_config_files(output_dir)
            return {"success": True, **config_results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_test_structure(self, output_dir: Path) -> Dict[str, Any]:
        """Create test structure (test compatibility method)."""
        try:
            test_results = self._create_tests(output_dir)
            return {"success": True, **test_results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_documentation(self, output_dir: Path) -> Dict[str, Any]:
        """Create documentation (test compatibility method)."""
        try:
            docs_results = self._create_documentation(output_dir)
            return {"success": True, **docs_results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration (test compatibility method)."""
        try:
            self.config.validate()
            return {"valid": True}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_template_content(self, template_name: str) -> Optional[str]:
        """Get template content (test compatibility method)."""
        try:
            template_path = self.templates_dir / template_name
            if template_path.exists():
                return template_path.read_text()
            return None
        except Exception:
            return None

    def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Render template with variables (test compatibility method)."""
        # First check if this is a Jinja2-style template with double braces
        if "{{" in template_content and "}}" in template_content:
            # Handle Jinja2-style templates manually
            result = template_content
            for key, value in variables.items():
                # Replace double brace patterns (Jinja2 style) {{ key }}
                result = result.replace(f"{{{{ {key} }}}}", str(value))  # {{ key }}
                result = result.replace(f"{{{{{key}}}}}", str(value))  # {{key}}
                result = result.replace(f"{{{{ {key}}}}}", str(value))  # {{ key}}
                result = result.replace(f"{{{{{key} }}}}", str(value))  # {{key }}

                # Handle extra spaces in double braces
                result = result.replace(f"{{{{  {key}  }}}}", str(value))  # {{  key  }}
                result = result.replace(f"{{{{   {key}   }}}}", str(value))  # {{   key   }}
            return result

        try:
            # For standard Python string formatting with single braces
            return template_content.format(**variables)
        except (KeyError, ValueError):
            # Fallback to manual variable replacement for single brace patterns
            result = template_content
            for key, value in variables.items():
                # Replace single brace patterns { key }
                result = result.replace(f"{{ {key} }}", str(value))  # { key }
                result = result.replace(f"{{{key}}}", str(value))  # {key}
                result = result.replace(f"{{ {key}}}", str(value))  # { key}
                result = result.replace(f"{{{key} }}", str(value))  # {key }

                # Handle extra spaces in single braces
                result = result.replace(f"{{  {key}  }}", str(value))  # {  key  }
                result = result.replace(f"{{   {key}   }}", str(value))  # {   key   }
            return result

    def create_file_from_template(
        self, template_content: str, file_path: Path, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create file from template (test compatibility method)."""
        try:
            rendered = self.render_template(template_content, variables)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(rendered)
            return {"success": True, "file_path": str(file_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_template_variables(self) -> Dict[str, Any]:
        """Get template variables (test compatibility method)."""
        return {
            "project_name": self.config.project_name,
            "package_name": self.config.package_name,
            "version": self.config.version,
            "author": self.config.author,
            "email": self.config.email,
            "description": self.config.description,
            "license": self.config.license,
            "python_requires": self.config.python_requires,
            "use_fastapi": self.config.use_fastapi,
            "use_docker": self.config.use_docker,
            "use_openai": self.config.use_openai,
            "create_tests": self.config.create_tests,
            "test_framework": self.config.test_framework,
        }

    def create_directory(self, directory_path: Path) -> Dict[str, Any]:
        """Create directory (test compatibility method)."""
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "directory": str(directory_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Write file (test compatibility method)."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return {"success": True, "file_path": str(file_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def initialize_git_repository(self, project_dir: Path) -> Dict[str, Any]:
        """Initialize git repository (test compatibility method)."""
        return self._initialize_git(project_dir)

    def generate_complete_project(self, output_dir: Path) -> Dict[str, Any]:
        """Generate complete project (test compatibility method)."""
        try:
            # Temporarily update config output_dir
            original_output_dir = self.config.output_dir
            self.config.output_dir = output_dir.parent

            results = self.generate()

            # Restore original output_dir
            self.config.output_dir = original_output_dir

            return {
                "success": True,
                "project_summary": {
                    "files_created": results.get("files_created", []),
                    "directories_created": results.get("directories_created", []),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _ensure_dependencies_installed(self) -> None:
        """Ensure all required dependencies are installed."""
        required_packages = ["fastapi", "uvicorn", "pydantic", "openai", "python-multipart"]

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                logger.warning(f"Required package {package} not found")

    def _create_secure_env_file(self, project_dir: Path) -> None:
        """Create secure environment file template."""
        env_template = """# OpenPypi Configuration
# Copy this file to .env and fill in your actual values

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key_here
OPENAI_ORGANIZATION=your_org_id_here

# PyPI Configuration  
PYPI_API_TOKEN=your_pypi_token_here
PYPI_REPOSITORY_URL=https://upload.pypi.org/legacy/

# Security Configuration
SECRET_KEY=your_secret_key_here_minimum_32_characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
"""

        env_file = project_dir / ".env.template"
        env_file.write_text(env_template)

        # Create .env with safe defaults if it doesn't exist
        actual_env_file = project_dir / ".env"
        if not actual_env_file.exists():
            safe_env = env_template.replace("your_", "safe_default_")
            actual_env_file.write_text(safe_env)

    def _create_production_dockerfile(self, project_dir: Path) -> None:
        """Create production-ready Dockerfile."""
        dockerfile_content = f"""# Multi-stage production Dockerfile
FROM python:3.11-slim as base

# Security updates
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Development stage
FROM base as development
WORKDIR /app
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "{self.config.package_name}.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
WORKDIR /app

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .

# Install application
RUN pip install -e .

# Switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
EXPOSE 8000
CMD ["gunicorn", "{self.config.package_name}.api:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# Distroless stage for minimal attack surface
FROM gcr.io/distroless/python3-debian11 as distroless
COPY --from=production /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=production /app /app
COPY --from=production /etc/passwd /etc/passwd
USER appuser
WORKDIR /app
EXPOSE 8000
ENTRYPOINT ["python", "-m", "{self.config.package_name}.api"]
"""

        dockerfile = project_dir / "Dockerfile.production"
        dockerfile.write_text(dockerfile_content)

    def _create_monitoring_config(self, project_dir: Path) -> None:
        """Create monitoring and observability configuration."""
        monitoring_content = """# Monitoring Configuration

version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"
    environment:
      - COLLECTOR_OTLP_ENABLED=true

volumes:
  grafana-storage:
"""

        monitoring_dir = project_dir / "monitoring"
        monitoring_dir.mkdir(exist_ok=True)

        (monitoring_dir / "docker-compose.monitoring.yml").write_text(monitoring_content)
