"""
Stage 4: Testing and Validation - Generate comprehensive tests and validation.
"""

import ast
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class ValidatorStage(BaseStage):
    """
    Stage 4: Testing and Validation

    This stage generates comprehensive test suites, validates the generated code,
    and ensures quality standards are met.
    """

    async def execute(self, context: PackageContext) -> None:
        """Execute the validation stage."""
        self.log_stage_start()

        try:
            # Get previous stage outputs
            concept_data = context.get_stage_output("p1_concept") or {}
            architecture_data = context.get_stage_output("p2_architecture") or {}
            implementation_data = context.get_stage_output("p3_implementation") or {}

            # Generate test suite
            test_data = await self._generate_test_suite(
                context, concept_data, architecture_data, implementation_data
            )

            # Validate generated code
            validation_results = await self._validate_code_quality(context)

            # Run static analysis
            analysis_results = await self._run_static_analysis(context)

            # Combine all validation data
            validation_data = {
                "tests": test_data,
                "code_quality": validation_results,
                "static_analysis": analysis_results,
                "overall_score": self._calculate_overall_score(
                    validation_results, analysis_results
                ),
            }

            if await self.validate_output(validation_data):
                # Write test files
                await self._write_test_files(context, test_data)

                # Generate additional validation files
                await self._generate_validation_configs(context)

                # Store stage output
                context.set_stage_output("p4_validation", validation_data)

                self.log_stage_end()
            else:
                raise ValueError("Validation failed - code quality below standards")

        except Exception as e:
            self.log_stage_error(e)
            raise

    async def _generate_test_suite(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
        implementation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive test suite."""
        test_data = {"test_files": {}}

        # Get modules to test
        modules = implementation_data.get("modules", {})

        for module_path, module_code in modules.items():
            if not module_path.startswith("tests/") and module_path.endswith(".py"):
                logger.info(f"Generating tests for {module_path}")

                test_code = await self._generate_module_tests(
                    context, module_path, module_code, concept_data
                )

                # Determine test file path
                test_file_path = self._get_test_file_path(module_path)
                test_data["test_files"][test_file_path] = test_code

        # Generate integration tests
        integration_tests = await self._generate_integration_tests(
            context, concept_data, architecture_data
        )
        test_data["test_files"]["tests/integration/test_integration.py"] = integration_tests

        return test_data

    async def _generate_module_tests(
        self,
        context: PackageContext,
        module_path: str,
        module_code: str,
        concept_data: Dict[str, Any],
    ) -> str:
        """Generate tests for a specific module."""
        system_prompt = self._get_test_system_prompt()
        user_prompt = self._get_test_user_prompt(context, module_path, module_code, concept_data)

        response = await self.provider.generate_response(
            prompt=user_prompt, system_prompt=system_prompt, temperature=0.4
        )

        return self._extract_code_from_response(response["content"])

    def _get_test_system_prompt(self) -> str:
        """Get system prompt for test generation."""
        return """You are an expert Python test engineer who writes comprehensive, maintainable test suites. You excel at:

        - Writing thorough unit tests with pytest
        - Creating meaningful test cases that cover edge cases
        - Using appropriate fixtures and mocking
        - Following testing best practices and patterns
        - Achieving high test coverage
        - Writing clear, descriptive test names and docstrings
        - Testing error conditions and exception handling
        - Creating integration tests for complex workflows

        Always generate tests that:
        1. Use pytest framework and conventions
        2. Include proper setup and teardown
        3. Test both happy path and error conditions
        4. Use appropriate assertions
        5. Mock external dependencies
        6. Have clear, descriptive test names
        7. Include docstrings explaining what is being tested
        8. Cover edge cases and boundary conditions
        9. Test async functions properly if applicable
        10. Follow AAA pattern (Arrange, Act, Assert)

        Generate complete, runnable test code with all necessary imports.
        """

    def _get_test_user_prompt(
        self,
        context: PackageContext,
        module_path: str,
        module_code: str,
        concept_data: Dict[str, Any],
    ) -> str:
        """Get user prompt for test generation."""
        return f"""Generate comprehensive pytest tests for the following Python module:

        **Module Path:** {module_path}
        **Package Name:** {context.package_name}
        **Package Description:** {concept_data.get('refined_description', context.idea)}

        **Module Code:**
        
        {module_code}
        

        **Requirements:**
        1. Test all public functions and methods
        2. Include tests for error conditions and edge cases
        3. Use appropriate fixtures for setup/teardown
        4. Mock external dependencies and I/O operations
        5. Test async functions properly if present
        6. Achieve high test coverage (aim for >90%)
        7. Use descriptive test names and docstrings
        8. Include parametrized tests where appropriate
        9. Test exception handling and error messages
        10. Follow pytest best practices

        **Test Structure:**
        - Use class-based organization for related tests
        - Include module-level fixtures if needed
        - Test both positive and negative scenarios
        - Include integration-style tests for complex functions
        - Test configuration and initialization code

        Generate complete test code with all necessary imports and fixtures.
        """

    def _get_test_file_path(self, module_path: str) -> str:
        """Get the corresponding test file path for a module."""
        # Convert src/package/module.py to tests/test_module.py
        path_parts = Path(module_path).parts
        if path_parts[0] == "src" and len(path_parts) > 2:
            # Skip src and package name parts
            module_parts = path_parts[2:]
            test_path = "tests/" + "/".join(module_parts)
            # Add test_ prefix to filename
            test_path = test_path.replace(".py", "")
            test_path = "/".join(
                test_path.split("/")[:-1] + [f"test_{test_path.split('/')[-1]}.py"]
            )
            return test_path
        else:
            # Fallback for other structures
            filename = Path(module_path).stem
            return f"tests/test_{filename}.py"

    async def _generate_integration_tests(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
    ) -> str:
        """Generate integration tests."""
        system_prompt = """You are an expert at creating integration tests that verify how components work together."""

        user_prompt = f"""Generate integration tests for the {context.package_name} package.

        **Package Description:** {concept_data.get('refined_description', context.idea)}
        **Architecture:** {architecture_data.get('structure', {})}

        Create tests that:
        1. Test end-to-end workflows
        2. Verify component interactions
        3. Test configuration loading
        4. Test error propagation
        5. Test async workflows if applicable
        6. Mock external services appropriately

        Generate complete integration test code with pytest.
        """

        response = await self.provider.generate_response(
            prompt=user_prompt, system_prompt=system_prompt, temperature=0.3
        )

        return self._extract_code_from_response(response["content"])

    async def _validate_code_quality(self, context: PackageContext) -> Dict[str, Any]:
        """Validate code quality of generated modules."""
        validation_results = {
            "syntax_valid": True,
            "import_errors": [],
            "quality_score": 10.0,
            "issues": [],
        }

        # Check syntax for all Python files
        for file_path in context.output_dir.rglob("*.py"):
            if file_path.name.startswith("test_"):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                validation_results["syntax_valid"] = False
                validation_results["issues"].append(f"Syntax error in {file_path}: {e}")
                validation_results["quality_score"] -= 2.0

        return validation_results

    async def _run_static_analysis(self, context: PackageContext) -> Dict[str, Any]:
        """Run static analysis tools."""
        analysis_results = {
            "flake8_score": 10.0,
            "mypy_score": 10.0,
            "bandit_score": 10.0,
            "overall_analysis_score": 10.0,
            "issues": [],
        }

        try:
            # Run flake8
            flake8_cmd = [
                "python",
                "-m",
                "flake8",
                str(context.output_dir / "src"),
                "--max-line-length=100",
                "--ignore=E203,W503",
            ]

            with tempfile.TemporaryDirectory() as temp_dir:
                result = subprocess.run(
                    flake8_cmd, capture_output=True, text=True, cwd=context.output_dir
                )

                if result.returncode != 0:
                    issues = result.stdout.split("\n")
                    analysis_results["issues"].extend(
                        [f"Flake8: {issue}" for issue in issues if issue]
                    )
                    analysis_results["flake8_score"] = max(0, 10 - len(issues) * 0.5)

        except Exception as e:
            logger.warning(f"Failed to run flake8: {e}")
            analysis_results["flake8_score"] = 5.0

        try:
            # Run mypy
            mypy_cmd = [
                "python",
                "-m",
                "mypy",
                str(context.output_dir / "src"),
                "--ignore-missing-imports",
            ]

            result = subprocess.run(
                mypy_cmd, capture_output=True, text=True, cwd=context.output_dir
            )

            if result.returncode != 0:
                issues = result.stdout.split("\n")
                analysis_results["issues"].extend([f"MyPy: {issue}" for issue in issues if issue])
                analysis_results["mypy_score"] = max(0, 10 - len(issues) * 0.3)

        except Exception as e:
            logger.warning(f"Failed to run mypy: {e}")
            analysis_results["mypy_score"] = 7.0

        try:
            # Run bandit for security analysis
            bandit_cmd = [
                "python",
                "-m",
                "bandit",
                "-r",
                str(context.output_dir / "src"),
                "-f",
                "json",
            ]

            result = subprocess.run(
                bandit_cmd, capture_output=True, text=True, cwd=context.output_dir
            )

            if result.stdout:
                bandit_data = json.loads(result.stdout)
                issues = bandit_data.get("results", [])
                high_severity = len([i for i in issues if i.get("issue_severity") == "HIGH"])
                medium_severity = len([i for i in issues if i.get("issue_severity") == "MEDIUM"])

                analysis_results["bandit_score"] = max(
                    0, 10 - high_severity * 2 - medium_severity * 1
                )

                for issue in issues:
                    analysis_results["issues"].append(
                        f"Bandit {issue.get('issue_severity', 'UNKNOWN')}: {issue.get('issue_text', '')}"
                    )

        except Exception as e:
            logger.warning(f"Failed to run bandit: {e}")
            analysis_results["bandit_score"] = 8.0

        # Calculate overall analysis score
        scores = [
            analysis_results["flake8_score"],
            analysis_results["mypy_score"],
            analysis_results["bandit_score"],
        ]
        analysis_results["overall_analysis_score"] = sum(scores) / len(scores)

        return analysis_results

    def _calculate_overall_score(
        self, validation_results: Dict[str, Any], analysis_results: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score."""
        quality_score = validation_results.get("quality_score", 0)
        analysis_score = analysis_results.get("overall_analysis_score", 0)

        # Weight the scores
        overall_score = (quality_score * 0.4) + (analysis_score * 0.6)

        # Penalty for syntax errors
        if not validation_results.get("syntax_valid", True):
            overall_score *= 0.5

        return round(overall_score, 2)

    async def _write_test_files(self, context: PackageContext, test_data: Dict[str, Any]) -> None:
        """Write test files to disk."""
        test_files = test_data.get("test_files", {})

        for test_file_path, test_content in test_files.items():
            file_path = context.output_dir / test_file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(test_content, encoding="utf-8")
            logger.info(f"Generated test file: {file_path}")

        # Generate conftest.py
        await self._generate_conftest(context)

    async def _generate_conftest(self, context: PackageContext) -> None:
        """Generate conftest.py with common fixtures."""
        conftest_content = f'''"""
Shared pytest fixtures for {context.package_name} tests.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_logger():
    """Provide a mock logger for tests."""
    return Mock()


@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {{
        "debug": True,
        "log_level": "INFO",
        "timeout": 30
    }}


@pytest.fixture
async def async_mock():
    """Provide an async mock for testing async functions."""
    mock = Mock()
    mock.__aenter__ = Mock(return_value=mock)
    mock.__aexit__ = Mock(return_value=None)
    return mock


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment before each test."""
    # Add any global setup/teardown here
    yield
    # Cleanup after test
'''

        conftest_path = context.output_dir / "tests" / "conftest.py"
        conftest_path.parent.mkdir(parents=True, exist_ok=True)
        conftest_path.write_text(conftest_content)
        logger.info(f"Generated conftest.py: {conftest_path}")

    async def _generate_validation_configs(self, context: PackageContext) -> None:
        """Generate validation configuration files."""

        # Generate pytest.ini
        pytest_ini_content = f"""[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=src/{context.package_name}
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests
    asyncio: marks tests as async tests
"""

        pytest_ini_path = context.output_dir / "pytest.ini"
        pytest_ini_path.write_text(pytest_ini_content)

        # Generate .coveragerc
        coveragerc_content = f"""[run]
source = src/{context.package_name}
omit = 
    */tests/*
    */test_*
    */__init__.py
    */conftest.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:

[html]
directory = htmlcov

[xml]
output = coverage.xml
"""

        coveragerc_path = context.output_dir / ".coveragerc"
        coveragerc_path.write_text(coveragerc_content)

        # Generate tox.ini for multi-environment testing
        tox_ini_content = f"""[tox]
envlist = py38,py39,py310,py311,py312,lint,type
isolated_build = True

[testenv]
deps = 
    pytest
    pytest-cov
    pytest-mock
commands = pytest {{posargs}}

[testenv:lint]
deps = 
    flake8
    black
    isort
commands = 
    flake8 src tests
    black --check src tests
    isort --check-only src tests

[testenv:type]
deps = 
    mypy
    types-all
commands = mypy src

[testenv:security]
deps = 
    bandit
    safety
commands = 
    bandit -r src
    safety check

[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,docs,build,dist
"""

        tox_ini_path = context.output_dir / "tox.ini"
        tox_ini_path.write_text(tox_ini_content)

        logger.info("Generated validation configuration files")

    def _extract_code_from_response(self, response_content: str) -> str:
        """Extract code from AI response."""
        import re

        # Look for code blocks
        code_block_pattern = r"```python\n(.*?)\n```"
        matches = re.findall(code_block_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Look for any code blocks
        code_block_pattern = r"```\n(.*?)\n```"
        matches = re.findall(code_block_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Fallback: return the entire response if no code blocks found
        return response_content.strip()

    async def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate the validation stage output."""
        overall_score = output.get("overall_score", 0)

        # Require minimum quality score
        if overall_score < 6.0:
            logger.error(f"Overall quality score {overall_score} below minimum threshold of 6.0")
            return False

        # Check that tests were generated
        test_files = output.get("tests", {}).get("test_files", {})
        if not test_files:
            logger.error("No test files generated")
            return False

        # Check syntax validity
        if not output.get("code_quality", {}).get("syntax_valid", False):
            logger.error("Generated code has syntax errors")
            return False

        return True

    def get_system_prompt(self) -> str:
        """Get the system prompt for validation."""
        return """You are an expert Python quality assurance engineer focused on comprehensive testing and validation."""

    def get_user_prompt(self, context: PackageContext) -> str:
        """Get the user prompt for validation."""
        return f"Generate comprehensive tests and validation for package: {context.package_name}"
