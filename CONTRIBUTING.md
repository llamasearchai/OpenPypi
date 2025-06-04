# Contributing to OpenPypi

Thank you for your interest in contributing to OpenPypi! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Contributions](#making-contributions)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)
- [Community](#community)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic knowledge of Python, FastAPI, Docker, and OpenAI APIs

### Types of Contributions

We welcome various types of contributions:

- **Bug Reports**: Report issues and bugs
- **Feature Requests**: Suggest new features or improvements
- **Documentation**: Improve documentation and examples
- **Testing**: Add or improve tests
- **Code**: Fix bugs or implement new features
- **Design**: Improve UI/UX for generated projects
- **Translations**: Help translate documentation
- **Providers**: Add new external service integrations

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/openpypi.git
cd openpypi
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .[dev,docs,test]

# Install pre-commit hooks
pre-commit install
```

### 3. Verify Setup

```bash
# Run tests to ensure everything works
pytest

# Check code formatting
black --check src tests
isort --check-only src tests
flake8 src tests

# Run the CLI
openpypi --help
```

### 4. Set Up Environment Variables (Optional)

For testing provider integrations:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=your_openai_key
# GITHUB_TOKEN=your_github_token
```

## Making Contributions

### Finding Issues to Work On

- Check the [Issues](https://github.com/openpypi/openpypi/issues) page
- Look for issues labeled `good first issue` for beginners
- Issues labeled `help wanted` are ready for contribution
- Check the [Project Board](https://github.com/openpypi/openpypi/projects) for planned features

### Creating Issues

Before creating a new issue:

1. Search existing issues to avoid duplicates
2. Use the appropriate issue template
3. Provide clear, detailed information
4. Include steps to reproduce for bugs
5. Add relevant labels

#### Bug Report Template

```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. With configuration '...'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., macOS, Ubuntu]
- Python version: [e.g., 3.11]
- OpenPypi version: [e.g., 1.0.0]

**Additional context**
Any other context about the problem.
```

#### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Additional context**
Any other context or screenshots about the feature request.
```

## Code Style and Standards

### Python Code Style

We follow [PEP 8](https://pep8.org/) with these tools:

- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting
- **pylint**: Additional linting
- **mypy**: Type checking

### Code Standards

#### 1. Type Hints

Use type hints for all public functions and methods:

```python
from typing import List, Dict, Optional, Any

def process_config(config: Dict[str, Any]) -> Optional[List[str]]:
    """Process configuration and return list of warnings."""
    # Implementation here
    pass
```

#### 2. Docstrings

Use Google-style docstrings:

```python
def generate_project(config: Config) -> GenerationResult:
    """Generate a new Python project.
    
    Args:
        config: Project configuration containing all settings.
        
    Returns:
        Generation result with created files and status.
        
    Raises:
        GenerationError: If project generation fails.
        ValidationError: If configuration is invalid.
    """
    pass
```

#### 3. Error Handling

Use specific exception types and meaningful error messages:

```python
from openpypi.core.exceptions import ValidationError

def validate_package_name(name: str) -> None:
    """Validate package name format."""
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValidationError(
            f"Invalid package name '{name}'. "
            "Package names must be alphanumeric with underscores or hyphens only."
        )
```

#### 4. Logging

Use the project's logging system:

```python
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)

def my_function():
    logger.info("Starting operation")
    try:
        # ... do work ...
        logger.debug("Operation completed successfully")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
```

### Commit Message Format

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(providers): add Azure provider integration
fix(cli): resolve configuration validation bug
docs(readme): update installation instructions
test(core): add tests for config validation
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openpypi --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run tests matching pattern
pytest -k "test_validation"

# Run tests in parallel
pytest -n auto
```

### Writing Tests

#### 1. Test Organization

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- API tests: `tests/api/`
- Fixtures: `tests/fixtures/`

#### 2. Test Structure

```python
import pytest
from unittest.mock import Mock, patch

from openpypi.core.config import Config
from openpypi.core.exceptions import ValidationError


class TestConfig:
    """Test cases for Config class."""
    
    def test_valid_configuration(self):
        """Test creating valid configuration."""
        config = Config(
            project_name="test_project",
            package_name="test_package",
            author="Test Author",
            email="test@example.com"
        )
        
        config.validate()  # Should not raise
        assert config.project_name == "test_project"
    
    def test_invalid_email_raises_error(self):
        """Test that invalid email raises ValidationError."""
        config = Config(
            project_name="test_project",
            email="invalid-email"
        )
        
        with pytest.raises(ValidationError, match="email must be a valid"):
            config.validate()
    
    @patch('openpypi.core.config.Path.exists')
    def test_config_from_file(self, mock_exists):
        """Test loading configuration from file."""
        mock_exists.return_value = True
        # Test implementation
```

#### 3. Test Fixtures

Use pytest fixtures for common test data:

```python
@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return Config(
        project_name="test_project",
        package_name="test_package",
        author="Test Author",
        email="test@example.com"
    )

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir
```

### Test Coverage

Maintain high test coverage (aim for >90%):

- All public methods should have tests
- Edge cases and error conditions should be tested
- Integration points should be tested
- Use mocks for external dependencies

## Documentation

### Types of Documentation

1. **API Documentation**: Docstrings in code (auto-generated)
2. **User Guide**: README.md and usage examples
3. **Developer Guide**: This file and technical documentation
4. **API Reference**: Generated from docstrings

### Writing Documentation

#### 1. Code Documentation

- All public functions/classes need docstrings
- Use Google-style docstrings
- Include examples for complex functions
- Document parameters, return values, and exceptions

#### 2. User Documentation

- Write clear, step-by-step instructions
- Include working code examples
- Explain the "why" not just the "how"
- Update documentation when adding features

#### 3. Examples

Provide practical examples:

```python
# Good example with context
from openpypi import OpenPypi
from openpypi.core.config import Config

# Create a FastAPI project with Docker support
config = Config(
    project_name="My API",
    package_name="my_api",
    author="Your Name",
    email="you@example.com",
    use_fastapi=True,
    use_docker=True
)

generator = OpenPypi(config)
result = generator.generate_project()
print(f"Created project at: {result.output_path}")
```

## Submitting Changes

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Changes**
   ```bash
   # Run all checks
   pytest
   black src tests
   isort src tests
   flake8 src tests
   pylint src
   mypy src
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(scope): description of changes"
   ```

5. **Push to Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Use the PR template
   - Link related issues
   - Add clear description of changes
   - Request review from maintainers

### Pull Request Guidelines

- Keep PRs focused and reasonably sized
- Include tests for new functionality
- Update documentation for user-facing changes
- Ensure all CI checks pass
- Respond to review feedback promptly

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated existing tests if needed

## Documentation
- [ ] Updated docstrings
- [ ] Updated README if needed
- [ ] Added examples if applicable

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Linked related issues
```

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Workflow

1. **Prepare Release**
   - Update `CHANGELOG.md`
   - Update version in `src/openpypi/_version.py`
   - Create release PR

2. **Create Release**
   - Merge release PR
   - Create GitHub release with tag
   - Automated CI publishes to PyPI

3. **Post-Release**
   - Update Docker images
   - Announce release
   - Update documentation

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and collaboration

### Getting Help

- Check existing documentation
- Search closed issues
- Ask in GitHub Discussions
- Contact maintainers for security issues

### Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- GitHub contributors page

## Development Tips

### Project Structure

```
openpypi/
├── src/openpypi/           # Main package
│   ├── core/               # Core functionality
│   ├── stages/             # Pipeline stages
│   ├── providers/          # External integrations
│   ├── api/                # FastAPI routes
│   └── utils/              # Utilities
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Development scripts
└── examples/               # Usage examples
```

### Debugging

Use the built-in logging system:

```python
import logging
from openpypi.utils.logger import setup_logging

# Enable debug logging
setup_logging("DEBUG")

# Use in code
logger = logging.getLogger(__name__)
logger.debug("Debug information")
```

### Local Testing

Test the CLI locally:

```bash
# Install in development mode
pip install -e .

# Test CLI commands
openpypi create test_project --use-fastapi
openpypi serve --reload
openpypi providers list
```

## FAQ

### Common Questions

**Q: How do I add a new provider?**
A: Create a new provider class inheriting from `Provider`, implement required methods, and register it in `providers/__init__.py`.

**Q: How do I add a new stage to the pipeline?**
A: Create a new stage class inheriting from `Stage`, implement the `execute` method, and add it to the appropriate pipeline.

**Q: How do I test my changes?**
A: Run `pytest` for unit tests, `openpypi create test_project` for integration testing.

**Q: My PR failed CI checks, what should I do?**
A: Check the CI logs, fix the issues locally, and push the fixes.

Thank you for contributing to OpenPypi! Your efforts help make Python development better for everyone. 