"""
Code formatting and style utilities for OpenPypi.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class CodeFormatter:
    """Formats Python code according to best practices."""

    def __init__(self):
        self.line_length = 100
        self.indent_size = 4
        self.quote_style = "double"

    def format_code(
        self, code: str, use_black: bool = True, use_isort: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Format Python code using black and isort.

        Args:
            code: Python code to format
            use_black: Whether to use black formatter
            use_isort: Whether to use isort for imports

        Returns:
            Tuple of (formatted_code, warnings)
        """
        warnings = []
        formatted_code = code

        try:
            # First, validate syntax
            ast.parse(code)
        except SyntaxError as e:
            warnings.append(f"Syntax error prevents formatting: {e}")
            return code, warnings

        # Apply isort for import sorting
        if use_isort:
            try:
                formatted_code = self._apply_isort(formatted_code)
            except Exception as e:
                warnings.append(f"isort formatting failed: {e}")

        # Apply black for code formatting
        if use_black:
            try:
                formatted_code = self._apply_black(formatted_code)
            except Exception as e:
                warnings.append(f"black formatting failed: {e}")

        # Fallback manual formatting if tools fail
        if warnings and formatted_code == code:
            formatted_code = self._manual_format(code)
            warnings.append("Used manual formatting as fallback")

        return formatted_code, warnings

    def _apply_black(self, code: str) -> str:
        """Apply black formatting."""
        try:
            import black

            mode = black.FileMode(
                line_length=self.line_length, string_normalization=True, is_pyi=False
            )

            return black.format_str(code, mode=mode)

        except ImportError:
            logger.warning("black not available, using manual formatting")
            return self._manual_format(code)
        except Exception as e:
            logger.warning(f"black formatting failed: {e}")
            return code

    def _apply_isort(self, code: str) -> str:
        """Apply isort for import sorting."""
        try:
            import isort

            config = isort.Config(
                profile="black",
                line_length=self.line_length,
                multi_line_output=3,
                include_trailing_comma=True,
                force_grid_wrap=0,
                use_parentheses=True,
                ensure_newline_before_comments=True,
            )

            return isort.code(code, config=config)

        except ImportError:
            logger.warning("isort not available, skipping import sorting")
            return code
        except Exception as e:
            logger.warning(f"isort formatting failed: {e}")
            return code

    def _manual_format(self, code: str) -> str:
        """Manual formatting as fallback."""
        lines = code.split("\n")
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue

            # Basic indentation handling
            if stripped.startswith(("def ", "class ", "if ", "for ", "while ", "with ", "try:")):
                formatted_lines.append(" " * (indent_level * self.indent_size) + stripped)
                if stripped.endswith(":"):
                    indent_level += 1
            elif stripped in ("else:", "elif ", "except:", "finally:"):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append(" " * (indent_level * self.indent_size) + stripped)
                indent_level += 1
            elif stripped == "return" or stripped.startswith("return "):
                formatted_lines.append(" " * (indent_level * self.indent_size) + stripped)
                indent_level = max(0, indent_level - 1)
            else:
                formatted_lines.append(" " * (indent_level * self.indent_size) + stripped)

        return "\n".join(formatted_lines)


class ProjectGenerator:
    """Generates complete Python project structure with templates."""

    def __init__(self):
        self.formatter = CodeFormatter()
        self.test_frameworks = {
            "pytest": self._generate_pytest_test,
            "unittest": self._generate_unittest_test,
        }

    def generate_example_usage(self, package_name: str) -> str:
        """Generate example usage code."""
        return f"""# Example usage of {package_name}
from {package_name} import AdvancedClass

instance = AdvancedClass()
instance.do_something()
"""

    def _generate_gitignore(self, package_name: str, metadata: Dict[str, Any]) -> str:
        """Generate .gitignore file."""
        return """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""

    def _generate_tests(
        self, project_dir: Path, package_name: str, modules: List[str], framework: str
    ) -> Dict[str, Any]:
        """Generate test files for a package."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        tests_dir = project_dir / "tests"

        # Create test directory structure
        test_dirs = [
            tests_dir,
            tests_dir / "unit",
            tests_dir / "integration",
            tests_dir / "fixtures",
        ]

        for test_dir in test_dirs:
            if not test_dir.exists():
                test_dir.mkdir(parents=True, exist_ok=True)
                results["directories_created"].append(str(test_dir.relative_to(project_dir)))

        # Create __init__.py files
        for test_dir in test_dirs:
            init_file = test_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""Test package."""\n')
                results["files_created"].append(str(init_file.relative_to(project_dir)))

        # Create conftest.py
        conftest_path = tests_dir / "conftest.py"
        if not conftest_path.exists():
            conftest_content = self._generate_conftest(package_name, framework)
            conftest_path.write_text(conftest_content)
            results["files_created"].append("tests/conftest.py")

        # Generate test files for each module
        generator = self.test_frameworks.get(framework, self._generate_pytest_test)

        for module in modules:
            # Unit tests
            unit_test_path = tests_dir / "unit" / f"test_{module}.py"
            if not unit_test_path.exists():
                test_content = generator(package_name, module, "unit")
                unit_test_path.write_text(test_content)
                results["files_created"].append(f"tests/unit/test_{module}.py")

            # Integration tests (for main modules)
            if module in ["core", "main", "__init__"]:
                integration_test_path = tests_dir / "integration" / f"test_{module}_integration.py"
                if not integration_test_path.exists():
                    integration_content = generator(package_name, module, "integration")
                    integration_test_path.write_text(integration_content)
                    results["files_created"].append(
                        f"tests/integration/test_{module}_integration.py"
                    )

        # Create test fixtures
        fixtures_path = tests_dir / "fixtures" / "sample_data.py"
        if not fixtures_path.exists():
            fixtures_content = self._generate_test_fixtures(package_name)
            fixtures_path.write_text(fixtures_content)
            results["files_created"].append("tests/fixtures/sample_data.py")

        return results

    def _generate_conftest(self, package_name: str, framework: str) -> str:
        """Generate conftest.py for pytest configuration."""
        if framework == "pytest":
            return f'''"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

import {package_name}


@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {{
        'string': 'test_string',
        'number': 42,
        'list': [1, 2, 3],
        'dict': {{'key': 'value'}}
    }}


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / 'test_file.txt'
    file_path.write_text('test content')
    return file_path


@pytest.fixture
def mock_config():
    """Provide mock configuration for tests."""
    return {{
        'debug': True,
        'timeout': 30,
        'retries': 3
    }}


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {{self.status_code}}")


@pytest.fixture
def mock_response():
    """Provide mock HTTP response."""
    return MockResponse({{'result': 'success'}})
'''
        else:
            return f'''"""Test configuration for unittest."""

import unittest
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

import {package_name}


class BaseTestCase(unittest.TestCase):
    """Base test case with common setup."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = {{
            'string': 'test_string',
            'number': 42,
            'list': [1, 2, 3],
            'dict': {{'key': 'value'}}
        }}
    
    def tearDown(self):
        """Clean up after tests."""
        pass
'''

    def _generate_pytest_test(self, package_name: str, module: str, test_type: str) -> str:
        """Generate pytest test file."""
        if test_type == "unit":
            return f'''"""Unit tests for {package_name}.{module} module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from {package_name} import {module}


class Test{module.title()}:
    """Test cases for {module} module."""
    
    def test_import(self):
        """Test that module can be imported."""
        assert {module} is not None
    
    def test_basic_functionality(self, sample_data):
        """Test basic functionality."""
        # Implementation note: Add comprehensive tests
        assert True
    
    def test_error_handling(self):
        """Test error handling."""
        # Implementation note: Test error conditions and edge cases
        with pytest.raises(ValueError):
            # Replace with actual error-inducing code
            raise ValueError("Test error")
    
    def test_edge_cases(self):
        """Test edge cases."""
        # TODO: Test edge cases
        assert True
    
    @patch('{package_name}.{module}.external_dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked dependencies."""
        mock_dependency.return_value = "mocked_result"
        # TODO: Test with mocked dependencies
        assert True
    
    @pytest.mark.parametrize("input_value,expected", [
        ("test1", "expected1"),
        ("test2", "expected2"),
        ("test3", "expected3"),
    ])
    def test_parametrized(self, input_value, expected):
        """Test with multiple parameter sets."""
        # TODO: Implement parametrized tests
        assert input_value is not None
        assert expected is not None
'''

        else:  # integration tests
            return f'''"""Integration tests for {package_name}.{module} module."""

import pytest
import tempfile
import os
from pathlib import Path

from {package_name} import {module}


class Test{module.title()}Integration:
    """Integration test cases for {module} module."""
    
    def test_full_workflow(self):
        """Test complete workflow integration."""
        # TODO: Implement full workflow test
        assert True
    
    def test_file_operations(self, tmp_path):
        """Test file operations integration."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # TODO: Test file operations
        assert test_file.exists()
    
    def test_external_dependencies(self):
        """Test integration with external dependencies."""
        # TODO: Test external integrations
        assert True
'''

    def _generate_unittest_test(self, package_name: str, module: str, test_type: str) -> str:
        """Generate unittest test file."""
        return f'''"""Unit tests for {package_name}.{module} module using unittest."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from {package_name} import {module}


class Test{module.title()}(unittest.TestCase):
    """Test cases for {module} module."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.sample_data = {{
            'string': 'test_string',
            'number': 42,
            'list': [1, 2, 3],
            'dict': {{'key': 'value'}}
        }}
    
    def tearDown(self):
        """Clean up after each test method."""
        pass
    
    def test_import(self):
        """Test that module can be imported."""
        self.assertIsNotNone({module})
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        # TODO: Implement actual tests
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
'''

    def _generate_test_fixtures(self, package_name: str) -> str:
        """Generate test fixtures file."""
        return f'''"""Test fixtures and sample data for {package_name} tests."""

import json
from pathlib import Path
from typing import Dict, List, Any


class SampleData:
    """Container for sample test data."""
    
    @staticmethod
    def get_simple_config() -> Dict[str, Any]:
        """Get simple configuration data."""
        return {{
            'debug': True,
            'timeout': 30,
            'retries': 3,
            'endpoints': {{
                'api': 'https://api.example.com',
                'auth': 'https://auth.example.com'
            }}
        }}
    
    @staticmethod
    def get_user_data() -> List[Dict[str, Any]]:
        """Get sample user data."""
        return [
            {{
                'id': 1,
                'name': 'John Doe',
                'email': 'john@example.com',
                'active': True
            }},
            {{
                'id': 2,
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'active': False
            }}
        ]
'''


class ConfigFormatter:
    """Formats and generates configuration files."""

    def __init__(self):
        self.config_formats = {
            "toml": self._generate_toml_config,
            "yaml": self._generate_yaml_config,
            "json": self._generate_json_config,
            "ini": self._generate_ini_config,
        }

    def generate_config_files(
        self,
        project_dir: Path,
        package_name: str,
        metadata: Dict[str, Any],
        formats: List[str] = None,
    ) -> Dict[str, Any]:
        """Generate configuration files in specified formats."""
        if formats is None:
            formats = ["toml"]

        results = {"files_created": [], "directories_created": [], "warnings": []}

        for format_type in formats:
            if format_type in self.config_formats:
                try:
                    format_results = self.config_formats[format_type](
                        project_dir, package_name, metadata
                    )
                    results["files_created"].extend(format_results.get("files_created", []))
                    results["directories_created"].extend(
                        format_results.get("directories_created", [])
                    )
                    results["warnings"].extend(format_results.get("warnings", []))
                except Exception as e:
                    results["warnings"].append(f"Failed to generate {format_type} config: {e}")
            else:
                results["warnings"].append(f"Unknown config format: {format_type}")

        return results

    def _generate_toml_config(
        self, project_dir: Path, package_name: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate TOML configuration files."""
        results = {"files_created": [], "directories_created": [], "warnings": []}

        # pyproject.toml (main project configuration)
        pyproject_path = project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            pyproject_content = self._generate_pyproject_toml(package_name, metadata)
            pyproject_path.write_text(pyproject_content)
            results["files_created"].append("pyproject.toml")

        return results

    def _generate_pyproject_toml(self, package_name: str, metadata: Dict[str, Any]) -> str:
        """Generate pyproject.toml content."""
        author = metadata.get("author", "Unknown Author")
        email = metadata.get("email", "author@example.com")
        description = metadata.get("description", f"{package_name} package")
        license_name = metadata.get("license", "MIT")
        python_requires = metadata.get("python_requires", ">=3.8")
        dependencies = metadata.get("dependencies", [])

        return f"""[build-system]
requires = ["setuptools>=69.0.0", "wheel", "setuptools-scm>=8.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_name}"
dynamic = ["version"]
description = "{description}"
readme = "README.md"
requires-python = "{python_requires}"
license = {{text = "{license_name}"}}
authors = [
    {{name = "{author}", email = "{email}"}},
]
maintainers = [
    {{name = "{author}", email = "{email}"}},
]
keywords = [
    "python",
    "package",
    "library"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: {license_name} License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = {dependencies}

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "pylint>=2.17.0",
    "mypy>=1.4.0",
]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.11.0",
]

[project.urls]
Homepage = "https://github.com/{author}/{package_name}"
Repository = "https://github.com/{author}/{package_name}.git"

[tool.setuptools]
package-dir = {{"" = "src"}}

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 100
target-version = ["py38", "py39", "py310", "py311", "py312"]

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]

[tool.coverage.run]
source = ["{package_name}"]
omit = ["tests/*"]
"""

    def _generate_yaml_config(
        self, project_dir: Path, package_name: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate YAML configuration files."""
        return {"files_created": [], "directories_created": [], "warnings": []}

    def _generate_json_config(
        self, project_dir: Path, package_name: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate JSON configuration files."""
        return {"files_created": [], "directories_created": [], "warnings": []}

    def _generate_ini_config(
        self, project_dir: Path, package_name: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate INI configuration files."""
        return {"files_created": [], "directories_created": [], "warnings": []}
