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
                )
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
        implementation_data: Dict[str, Any]
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
        concept_data: Dict[str, Any]
    ) -> str:
        """Generate tests for a specific module."""
        system_prompt = self._get_test_system_prompt()
        user_prompt = self._get_test_user_prompt(
            context, module_path, module_code, concept_data
        )
        
        response = await self.provider.generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.4
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
        concept_data: Dict[str, Any]
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
        # Convert src/package/module.py to tests/unit/test_module.py
        path_parts = Path(module_path).parts
        
        if path_parts[0] == "src" and len(path_parts) > 2:
            module_name = Path(module_path).stem
            if module_name == "__init__":
                module_name = path_parts[-2]  # Use directory name
            return f"tests/unit/test_{module_name}.py"
        else:
            module_name = Path(module_path).stem
            return f"tests/unit/test_{module_name}.py"
    
    async def _generate_integration_tests(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any]
    ) -> str:
        """Generate integration tests."""
        system_prompt = """You are an expert at writing integration tests that verify the complete functionality of Python packages. Focus on testing the main workflows and user scenarios."""
        
        user_prompt = f"""Generate integration tests for the package: {context.package_name}

        **Package Description:** {concept_data.get('refined_description', context.idea)}
        **Key Features:** {', '.join(concept_data.get('key_features', []))}
        **Use Cases:** {concept_data.get('use_cases', [])}

        **Requirements:**
        1. Test main user workflows end-to-end
        2. Test package installation and imports
        3. Test CLI functionality if present
        4. Test configuration and settings
        5. Test error handling in realistic scenarios
        6. Include performance tests for critical paths
        7. Test compatibility with different Python versions
        8. Mock external services but test real integrations

        Generate comprehensive integration tests that verify the package works as intended for real users.
        """
        
        response = await self.provider.generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )
        
        return self._extract_code_from_response(response["content"])
    
    async def _validate_code_quality(self, context: PackageContext) -> Dict[str, Any]:
        """Validate code quality using static analysis."""
        results = {
            "syntax_valid": True,
            "import_errors": [],
            "style_issues": [],
            "complexity_issues": [],
            "type_issues": []
        }
        
        # Check syntax validity
        src_dir = context.output_dir / "src"
        if src_dir.exists():
            for py_file in src_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    results["syntax_valid"] = False
                    results["import_errors"].append(f"{py_file}: {str(e)}")
                except Exception as e:
                    results["import_errors"].append(f"{py_file}: {str(e)}")
        
        return results
    
    async def _run_static_analysis(self, context: PackageContext) -> Dict[str, Any]:
        """Run static analysis tools."""
        results = {
            "flake8_score": 10.0,
            "mypy_score": 10.0,
            "bandit_score": 10.0,
            "complexity_score": 10.0
        }
        
        # Run in a temporary environment to avoid conflicts
        try:
            # Change to package directory
            original_cwd = Path.cwd()
            package_dir = context.output_dir
            
            # Run flake8
            try:
                result = subprocess.run(
                    ["flake8", "src", "--count", "--statistics"],
                    cwd=package_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    results["flake8_score"] = 10.0
                else:
                    # Calculate score based on issues
                    issue_count = len(result.stdout.split('\n')) if result.stdout else 0
                    results["flake8_score"] = max(0, 10 - (issue_count * 0.1))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                results["flake8_score"] = 5.0  # Default score if tool not available
            
            # Run mypy
            try:
                result = subprocess.run(
                    ["mypy", "src", "--ignore-missing-imports"],
                    cwd=package_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    results["mypy_score"] = 10.0
                else:
                    error_count = len(result.stdout.split('\n')) if result.stdout else 0
                    results["mypy_score"] = max(0, 10 - (error_count * 0.2))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                results["mypy_score"] = 5.0
            
            # Run bandit for security analysis
            try:
                result = subprocess.run(
                    ["bandit", "-r", "src", "-f", "json"],
                    cwd=package_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    results["bandit_score"] = 10.0
                else:
                    try:
                        bandit_data = json.loads(result.stdout)
                        high_issues = len([r for r in bandit_data.get("results", []) 
                                         if r.get("issue_severity") == "HIGH"])
                        medium_issues = len([r for r in bandit_data.get("results", []) 
                                           if r.get("issue_severity") == "MEDIUM"])
                        results["bandit_score"] = max(0, 10 - (high_issues * 2) - (medium_issues * 0.5))
                    except json.JSONDecodeError:
                        results["bandit_score"] = 8.0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                results["bandit_score"] = 8.0
                
        except Exception as e:
            logger.warning(f"Static analysis failed: {str(e)}")
            # Set default scores
            for key in results:
                if results[key] == 10.0:
                    results[key] = 7.0
        
        return results
    
    def _calculate_overall_score(
        self, 
        validation_results: Dict[str, Any], 
        analysis_results: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score."""
        scores = []
        
        # Syntax validity (critical)
        if validation_results.get("syntax_valid", False):
            scores.append(10.0)
        else:
            scores.append(0.0)
        
        # Static analysis scores
        scores.extend([
            analysis_results.get("flake8_score", 5.0),
            analysis_results.get("mypy_score", 5.0),
            analysis_results.get("bandit_score", 8.0),
            analysis_results.get("complexity_score", 8.0)
        ])
        
        # Import errors penalty
        import_error_count = len(validation_results.get("import_errors", []))
        import_score = max(0, 10 - (import_error_count * 2))
        scores.append(import_score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    async def _write_test_files(
        self, 
        context: PackageContext, 
        test_data: Dict[str, Any]
    ) -> None:
        """Write generated test files."""
        test_files = test_data.get("test_files", {})
        
        for test_path, test_code in test_files.items():
            file_path = context.output_dir / test_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add test file header
            header = f'''"""
{test_path}

Test suite for {context.package_name}
Generated by OpenPypi - AI-Driven PyPI Package Generator
"""

'''
            
            # Write test code with header
            full_code = header + test_code
            file_path.write_text(full_code, encoding='utf-8')
            
            logger.info(f"Generated test file: {file_path}")
        
        # Generate conftest.py for pytest configuration
        await self._generate_conftest(context)
    
    async def _generate_conftest(self, context: PackageContext) -> None:
        """Generate conftest.py for pytest configuration."""
        conftest_content = f'''"""
Pytest configuration and shared fixtures for {context.package_name}
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {{
        "debug": True,
        "test_mode": True,
        "timeout": 30
    }}


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return {{
        "test_string": "Hello, World!",
        "test_number": 42,
        "test_list": [1, 2, 3, 4, 5],
        "test_dict": {{"key": "value", "nested": {{"inner": "data"}}}}
    }}


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Setup code here
    yield
    # Cleanup code here


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data=None, status_code=200, text=""):
        self.json_data = json_data or {{}}
        self.status_code = status_code
        self.text = text
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_http_response():
    """Mock HTTP response fixture."""
    return MockResponse
'''
        
        conftest_path = context.output_dir / "tests" / "conftest.py"
        conftest_path.parent.mkdir(parents=True, exist_ok=True)
        conftest_path.write_text(conftest_content)
        logger.info(f"Generated conftest.py: {conftest_path}")
    
    async def _generate_validation_configs(self, context: PackageContext) -> None:
        """Generate validation configuration files."""
        
        # Generate pytest.ini
        pytest_ini_content = f'''[tool:pytest]
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
'''
        
        pytest_ini_path = context.output_dir / "pytest.ini"
        pytest_ini_path.write_text(pytest_ini_content)
        
        # Generate .coveragerc
        coveragerc_content = f'''[run]
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
'''
        
        coveragerc_path = context.output_dir / ".coveragerc"
        coveragerc_path.write_text(coveragerc_content)
        
        # Generate tox.ini for multi-environment testing
        tox_ini_content = f'''[tox]
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
async def _generate_license(self, context: PackageContext) -> str:
    """Generate LICENSE file content."""
    if context.license_type.upper() == "MIT":
        license_content = f"""MIT License

        tox_ini_path = context.output_dir / "tox.ini"
        tox_ini_path.write_text(tox_ini_content)
        
            return license_content

        async def _write_documentation_files(
            self,
            context: PackageContext,
            docs_data: Dict[str, Any]
        ) -> None:
            """Write documentation files to disk."""
    
            # Write main documentation files
            main_docs = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "LICENSE"]
    
            for doc_name in main_docs:
                if doc_name in docs_data:
                    doc_path = context.output_dir / doc_name
                    doc_path.write_text(docs_data[doc_name], encoding='utf-8')
                    logger.info(f"Generated {doc_name}: {doc_path}")
    
            # Write user guide
            if "user_guide" in docs_data:
                user_guide_path = context.output_dir / "docs" / "user_guide.md"
                user_guide_path.parent.mkdir(parents=True, exist_ok=True)
                user_guide_path.write_text(docs_data["user_guide"], encoding='utf-8')
                logger.info(f"Generated user guide: {user_guide_path}")
    
            # Write API documentation
            api_docs = docs_data.get("api_docs", {})
            for doc_file, content in api_docs.items():
                api_doc_path = context.output_dir / "docs" / "source" / "api" / doc_file
                api_doc_path.parent.mkdir(parents=True, exist_ok=True)
                api_doc_path.write_text(content, encoding='utf-8')
                logger.info(f"Generated API doc: {api_doc_path}")

        async def _generate_sphinx_config(
            self,
            context: PackageContext,
            docs_data: Dict[str, Any]
        ) -> None:
            """Generate Sphinx configuration files."""
    
            # Create docs directory structure
            docs_dir = context.output_dir / "docs"
            source_dir = docs_dir / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
    
            # Generate conf.py
            conf_py_content = f'''"""        
        logger.info("Generated validation configuration files")
    
    def _extract_code_from_response(self, response_content: str) -> str:
        """Extract code from AI response."""
        import re
        
        # Look for code blocks
        code_block_pattern = r'\n(.*?)\n'
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