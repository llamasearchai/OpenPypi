"""
Stage 3: Package Implementation - Generate the actual package code.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class PackagerStage(BaseStage):
    """
    Stage 3: Package Implementation

    This stage generates the actual Python code for the package,
    including all modules, classes, functions, and implementation details.
    """

    async def execute(self, context: PackageContext) -> None:
        """Execute the package implementation stage."""
        self.log_stage_start()

        try:
            # Get previous stage outputs
            concept_data = context.get_stage_output("p1_concept") or {}
            architecture_data = context.get_stage_output("p2_architecture") or {}

            # Generate implementation for each module
            implementation_data = await self._generate_implementation(
                context, concept_data, architecture_data
            )

            if await self.validate_output(implementation_data):
                # Write code files
                await self._write_code_files(context, implementation_data)

                # Generate configuration files
                await self._generate_config_files(context, architecture_data)

                # Store stage output
                context.set_stage_output("p3_implementation", implementation_data)

                self.log_stage_end()
            else:
                raise ValueError("Invalid implementation output generated")

        except Exception as e:
            self.log_stage_error(e)
            raise

    async def _generate_implementation(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate implementation for all modules."""
        implementation_data = {"modules": {}}

        # Get package structure
        package_structure = architecture_data.get("package_structure", {})
        api_design = architecture_data.get("api_design", {})

        # Generate code for each module
        for module_path, module_info in self._extract_python_files(package_structure):
            if module_path.endswith(".py"):
                logger.info(f"Generating code for {module_path}")

                module_code = await self._generate_module_code(
                    context, module_path, module_info, concept_data, api_design
                )

                implementation_data["modules"][module_path] = module_code

        return implementation_data

    def _extract_python_files(self, structure: Dict[str, Any], prefix: str = "") -> List[tuple]:
        """Extract Python files from package structure."""
        files = []

        for name, content in structure.items():
            full_path = f"{prefix}/{name}" if prefix else name

            if isinstance(content, dict):
                files.extend(self._extract_python_files(content, full_path))
            elif name.endswith(".py"):
                files.append((full_path, content))

        return files

    async def _generate_module_code(
        self,
        context: PackageContext,
        module_path: str,
        module_info: str,
        concept_data: Dict[str, Any],
        api_design: Dict[str, Any],
    ) -> str:
        """Generate code for a specific module."""
        system_prompt = self.get_system_prompt()
        user_prompt = self._get_module_prompt(
            context, module_path, module_info, concept_data, api_design
        )

        response = await self.provider.generate_response(
            prompt=user_prompt, system_prompt=system_prompt, temperature=0.5
        )

        # Extract code from response
        code = self._extract_code_from_response(response["content"])
        return code

    def get_system_prompt(self) -> str:
        """Get the system prompt for code generation."""
        return """You are an expert Python developer who writes production-quality code. You excel at:

        - Writing clean, readable, and maintainable Python code
        - Following PEP 8 style guidelines and Python best practices
        - Implementing proper error handling and logging
        - Using type hints throughout the codebase
        - Writing comprehensive docstrings (Google style)
        - Implementing appropriate design patterns
        - Creating secure and efficient code
        - Following SOLID principles

        Always generate code that:
        1. Is syntactically correct and follows PEP 8
        2. Includes comprehensive type hints
        3. Has detailed docstrings for all public APIs
        4. Implements proper error handling
        5. Uses appropriate logging
        6. Is well-structured and modular
        7. Includes security considerations
        8. Is compatible with the specified Python version

        Respond with only the Python code, properly formatted and commented.
        """

    def _get_module_prompt(
        self,
        context: PackageContext,
        module_path: str,
        module_info: str,
        concept_data: Dict[str, Any],
        api_design: Dict[str, Any],
    ) -> str:
        """Get the user prompt for module code generation."""

        # Determine module type and purpose
        module_name = Path(module_path).stem
        is_init = module_name == "__init__"
        is_main = module_name in ["main", "core"]
        is_cli = "cli" in module_path
        is_test = "test" in module_path

        base_prompt = f"""Generate Python code for the module: {module_path}

        **Package Context:**
        - Package Name: {context.package_name}
        - Description: {concept_data.get('refined_description', context.idea)}
        - Python Version: {context.python_version}
        - Package Type: {context.package_type}
        - Features: {', '.join(context.features)}

        **Module Purpose:** {module_info}

        **Key Features to Implement:**
        {chr(10).join(f"- {feature}" for feature in concept_data.get('key_features', []))}

        **API Design Context:**
        - Public Classes: {len(api_design.get('public_classes', []))} classes
        - Public Functions: {len(api_design.get('public_functions', []))} functions
        """

        if is_init:
            return (
                base_prompt
                + """
        
        **Requirements for __init__.py:**
        1. Import and expose the main public API
        2. Define __version__, __author__, __email__
        3. Include a module-level docstring
        4. Set up __all__ list for explicit exports
        5. Handle any initialization logic
        6. Import key classes and functions for easy access
        
        Example structure:
        
        \"\"\"Package description.\"\"\"
        
        __version__ = "0.1.0"
        __author__ = "Author Name"
        __email__ = "nikjois@llamasearch.ai"
        
        from .core import MainClass, main_function
        from .exceptions import CustomError
        
        __all__ = ["MainClass", "main_function", "CustomError"]
        
        """
            )

        elif is_main or module_name == "core":
            return (
                base_prompt
                + f"""
        
        **Requirements for core module:**
        1. Implement the main functionality described in the concept
        2. Create classes and functions as specified in the API design
        3. Include comprehensive error handling
        4. Add logging throughout
        5. Use type hints for all functions and methods
        6. Follow async patterns if specified: {concept_data.get('technical_considerations', {}).get('async_support', False)}
        
        **Classes to implement:**
        {chr(10).join(f"- {cls['name']}: {cls['purpose']}" for cls in api_design.get('public_classes', []))}
        
        **Functions to implement:**
        {chr(10).join(f"- {func['name']}: {func['purpose']}" for func in api_design.get('public_functions', []))}
        """
            )

        elif is_cli:
            return (
                base_prompt
                + """
        
        **Requirements for CLI module:**
        1. Use Click or argparse for command-line interface
        2. Implement subcommands if appropriate
        3. Add help text and examples
        4. Handle command-line arguments and options
        5. Provide clear error messages
        6. Include progress indicators for long operations
        7. Support configuration files
        
        Example structure with Click:
        
        import click
        
        @click.group()
        def cli():
            \"\"\"Main CLI entry point.\"\"\"
            pass
        
        @cli.command()
        @click.option('--option', help='Description')
        def command(option):
            \"\"\"Command description.\"\"\"
            pass
        
        """
            )

        elif is_test:
            return (
                base_prompt
                + """
        
        **Requirements for test module:**
        1. Use pytest framework
        2. Test all public functions and methods
        3. Include edge cases and error conditions
        4. Use fixtures for setup and teardown
        5. Mock external dependencies
        6. Aim for high test coverage
        7. Include integration tests where appropriate
        
        Example structure:
        
        import pytest
        from unittest.mock import Mock, patch
        
        from package_name import MainClass
        
        class TestMainClass:
            def test_method(self):
                \"\"\"Test method description.\"\"\"
                # Test implementation
                pass
        
        """
            )

        elif module_name == "exceptions":
            return (
                base_prompt
                + """
        
        **Requirements for exceptions module:**
        1. Define custom exception hierarchy
        2. Inherit from appropriate base exceptions
        3. Include helpful error messages
        4. Add context information to exceptions
        5. Document when each exception is raised
        
        Example structure:
        
        class PackageError(Exception):
            \"\"\"Base exception for package.\"\"\"
            pass
        
        class ValidationError(PackageError):
            \"\"\"Raised when validation fails.\"\"\"
            pass
        
        """
            )

        elif module_name in ["utils", "helpers"]:
            return (
                base_prompt
                + """
        
        **Requirements for utilities module:**
        1. Implement helper functions used across the package
        2. Include validation functions
        3. Add utility classes if needed
        4. Ensure functions are pure when possible
        5. Include comprehensive error handling
        6. Add type hints and docstrings
        """
            )

        else:
            return (
                base_prompt
                + f"""
        
        **Requirements for {module_name} module:**
        1. Implement functionality specific to this module
        2. Follow the package's overall architecture
        3. Include proper error handling and logging
        4. Use type hints throughout
        5. Add comprehensive docstrings
        6. Ensure compatibility with the rest of the package
        """
            )

        return (
            base_prompt
            + """
        
        Please generate complete, production-ready Python code for this module.
        Include all necessary imports, proper error handling, logging, type hints, and docstrings.
        """
        )

    def _extract_code_from_response(self, response_content: str) -> str:
        """Extract Python code from AI response."""
        # Look for code blocks
        code_block_pattern = r"\n(.*?)\n"
        matches = re.findall(code_block_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Look for code without explicit blocks
        lines = response_content.split("\n")
        code_lines = []
        in_code = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                continue

            if in_code or line.startswith("    ") or line.startswith("\t"):
                code_lines.append(line)
            elif line.strip() and not any(
                word in line.lower() for word in ["here", "this", "the", "above"]
            ):
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines).strip()

        # Fallback: return the entire response
        return response_content.strip()

    async def _write_code_files(
        self, context: PackageContext, implementation_data: Dict[str, Any]
    ) -> None:
        """Write generated code to files."""
        modules = implementation_data.get("modules", {})

        for module_path, code in modules.items():
            file_path = context.output_dir / module_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Add file header
            header = f'''"""
{module_path}

Generated by OpenPypi - AI-Driven PyPI Package Generator
Package: {context.package_name}
"""

'''

            # Write code with header
            full_code = header + code
            file_path.write_text(full_code, encoding="utf-8")

            logger.info(f"Generated code file: {file_path}")

    async def _generate_config_files(
        self, context: PackageContext, architecture_data: Dict[str, Any]
    ) -> None:
        """Generate configuration files (pyproject.toml, setup.py, etc.)."""

        # Generate pyproject.toml
        await self._generate_pyproject_toml(context, architecture_data)

        # Generate setup.py for backward compatibility
        await self._generate_setup_py(context, architecture_data)

        # Generate requirements files
        await self._generate_requirements_files(context, architecture_data)

        # Generate other config files
        await self._generate_other_configs(context, architecture_data)

    async def _generate_pyproject_toml(
        self, context: PackageContext, architecture_data: Dict[str, Any]
    ) -> None:
        """Generate pyproject.toml file."""
        dependencies = architecture_data.get("dependencies", {})
        core_deps = dependencies.get("core", [])
        optional_deps = dependencies.get("optional", {})

        # Get entry points
        api_design = architecture_data.get("api_design", {})
        entry_points = api_design.get("entry_points", {})
        console_scripts = entry_points.get("console_scripts", [])

        pyproject_content = f"""[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{context.package_name}"
version = "{context.version}"
description = "{context.description}"
readme = "README.md"
requires-python = "{context.python_version}"
license = {{text = "{context.license_type}"}}
authors = [
    {{name = "{context.author}", email = "{context.email}"}},
]
keywords = {context.keywords}
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
dependencies = {core_deps}

[project.urls]
Homepage = "https://github.com/{context.author.lower().replace(' ', '')}/{context.package_name}"
Repository = "https://github.com/{context.author.lower().replace(' ', '')}/{context.package_name}"
Issues = "https://github.com/{context.author.lower().replace(' ', '')}/{context.package_name}/issues"

[project.optional-dependencies]
"""

        # Add optional dependencies
        for category, deps in optional_deps.items():
            pyproject_content += f"{category} = {deps}\n"

        # Add console scripts if any
        if console_scripts:
            pyproject_content += "\n[project.scripts]\n"
            for script in console_scripts:
                pyproject_content += f"{script}\n"

        pyproject_content += """
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-dir]
"" = "src"

[tool.black]
line-length = 88
target-version = ["py38"]

[tool.isort]
profile = "black"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--strict-markers --cov=src --cov-report=term-missing"

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
"""

        pyproject_path = context.output_dir / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)
        logger.info(f"Generated pyproject.toml: {pyproject_path}")

    async def _generate_setup_py(
        self, context: PackageContext, architecture_data: Dict[str, Any]
    ) -> None:
        """Generate setup.py for backward compatibility."""
        setup_content = f'''"""Setup script for {context.package_name}."""

from setuptools import setup, find_packages

setup(
    name="{context.package_name}",
    version="{context.version}",
    description="{context.description}",
    author="{context.author}",
    author_email="{context.email}",
    packages=find_packages(where="src"),
    package_dir={{"": "src"}},
    python_requires="{context.python_version}",
    install_requires={architecture_data.get("dependencies", {}).get("core", [])},
    extras_require={architecture_data.get("dependencies", {}).get("optional", {})},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
)
'''

        setup_path = context.output_dir / "setup.py"
        setup_path.write_text(setup_content)
        logger.info(f"Generated setup.py: {setup_path}")

    async def _generate_requirements_files(
        self, context: PackageContext, architecture_data: Dict[str, Any]
    ) -> None:
        """Generate requirements.txt and requirements-dev.txt files."""
        dependencies = architecture_data.get("dependencies", {})

        # requirements.txt
        core_deps = dependencies.get("core", [])
        if core_deps:
            req_content = "\n".join(core_deps) + "\n"
            req_path = context.output_dir / "requirements.txt"
            req_path.write_text(req_content)
            logger.info(f"Generated requirements.txt: {req_path}")

        # requirements-dev.txt
        dev_deps = dependencies.get("optional", {}).get("dev", [])
        default_dev_deps = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ]

        all_dev_deps = list(set(dev_deps + default_dev_deps))
        dev_req_content = "\n".join(all_dev_deps) + "\n"
        dev_req_path = context.output_dir / "requirements-dev.txt"
        dev_req_path.write_text(dev_req_content)
        logger.info(f"Generated requirements-dev.txt: {dev_req_path}")

    async def _generate_other_configs(
        self, context: PackageContext, architecture_data: Dict[str, Any]
    ) -> None:
        """Generate other configuration files."""

        # .gitignore
        gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
"""

        gitignore_path = context.output_dir / ".gitignore"
        gitignore_path.write_text(gitignore_content)
        logger.info(f"Generated .gitignore: {gitignore_path}")

        # MANIFEST.in
        manifest_content = """include README.md
include LICENSE
include requirements*.txt
recursive-include src *.py
recursive-include tests *.py
recursive-include docs *.rst *.md *.txt *.py
recursive-exclude * __pycache__
recursive-exclude * *.py[co]
"""

        manifest_path = context.output_dir / "MANIFEST.in"
        manifest_path.write_text(manifest_content)
        logger.info(f"Generated MANIFEST.in: {manifest_path}")

    async def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate the implementation output."""
        modules = output.get("modules", {})

        if not modules:
            logger.error("No modules generated")
            return False

        # Check for required files
        required_files = ["__init__.py"]
        for required_file in required_files:
            if not any(required_file in path for path in modules.keys()):
                logger.error(f"Missing required file: {required_file}")
                return False

        # Validate that code is not empty
        for module_path, code in modules.items():
            if not code or len(code.strip()) < 10:
                logger.error(f"Generated code for {module_path} is too short or empty")
                return False

        return True

    def get_user_prompt(self, context: PackageContext) -> str:
        """Get the user prompt for this stage."""
        return "Generate package implementation based on architecture design."
