#!/usr/bin/env python3
"""
Complete setup script for OpenPypi project.
This script handles dependency installation, testing, building, and publication preparation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd: str, cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command with proper error handling."""
    print(f"RUNNING: {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"SUCCESS: Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version < (3, 8):
        print(f"ERROR: Python {version.major}.{version.minor} is not supported. Please use Python 3.8+")
        sys.exit(1)
    print(f"SUCCESS: Python {version.major}.{version.minor}.{version.micro} is compatible")

def setup_environment():
    """Set up the development environment."""
    print("SETUP: Setting up development environment...")
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"DIRECTORY: Working directory: {project_root}")
    
    # Create virtual environment if it doesn't exist
    venv_path = project_root / "venv"
    if not venv_path.exists():
        print("SETUP: Creating virtual environment...")
        run_command(f"{sys.executable} -m venv venv")
    
    # Get the correct pip path
    if os.name == 'nt':  # Windows
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:  # Unix-like
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    return pip_path, python_path

def install_dependencies(pip_path):
    """Install all required dependencies."""
    print("INSTALLING: Installing dependencies...")
    
    # Upgrade pip first
    run_command(f"{pip_path} install --upgrade pip")
    
    # Install development dependencies
    run_command(f"{pip_path} install -r requirements-dev.txt")
    
    # Install package in development mode
    run_command(f"{pip_path} install -e .")
    
    print("SUCCESS: Dependencies installed successfully!")

def run_tests(python_path):
    """Run the complete test suite."""
    print("TESTING: Running test suite...")
    
    # Clean up any previous test artifacts
    for pattern in [".coverage*", "htmlcov", ".pytest_cache"]:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
    
    # Run tests without coverage first to avoid issues
    result = run_command(f"{python_path} -m pytest tests/ --tb=short -v", check=False)
    
    if result.returncode != 0:
        print("WARNING: Some tests failed, but continuing with setup...")
    else:
        print("SUCCESS: All tests passed!")
    
    return result.returncode == 0

def run_code_quality_checks(python_path):
    """Run code quality checks."""
    print("CHECKING: Running code quality checks...")
    
    checks = [
        ("Black formatting", f"{python_path} -m black --check src tests"),
        ("Import sorting", f"{python_path} -m isort --check-only src tests"),
        ("Flake8 linting", f"{python_path} -m flake8 src tests --max-line-length=100"),
        ("Security scan", f"{python_path} -m bandit -r src -f txt"),
    ]
    
    all_passed = True
    for check_name, command in checks:
        print(f"  CHECKING: {check_name}...")
        result = run_command(command, check=False)
        if result.returncode != 0:
            print(f"    WARNING: {check_name} issues found")
            all_passed = False
        else:
            print(f"    SUCCESS: {check_name} passed")
    
    return all_passed

def build_package(python_path):
    """Build the package for distribution."""
    print("BUILDING: Building package...")
    
    # Clean previous builds
    for pattern in ["build", "dist", "*.egg-info"]:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
    
    # Build package
    run_command(f"{python_path} -m build")
    
    # Check built package
    dist_files = list(Path("dist").glob("*"))
    print(f"SUCCESS: Built package files: {[f.name for f in dist_files]}")
    
    return len(dist_files) > 0

def create_env_template():
    """Create environment template file."""
    print("🔐 Creating environment template...")
    
    env_template = """# OpenPypi Environment Configuration
# Copy this file to .env and fill in your actual values

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ORGANIZATION=your_openai_org_id_here

# PyPI Publishing
PYPI_API_TOKEN=your_pypi_api_token_here
PYPI_REPOSITORY_URL=https://upload.pypi.org/legacy/

# Security
SECRET_KEY=your_secret_key_here_32_chars_minimum
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///openpypi.db
REDIS_URL=redis://localhost:6379/0

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
"""
    
    env_template_path = Path(".env.template")
    env_template_path.write_text(env_template)
    
    if not Path(".env").exists():
        Path(".env").write_text(env_template.replace("your_", "dev_"))
        print("SUCCESS: Created .env file with development defaults")
    
    print("SUCCESS: Environment template created")

def print_next_steps():
    """Print next steps for the user."""
    print("\nSUCCESS: Setup complete!")
    print("\nNEXT STEPS:")
    print("1. Update .env file with your actual API keys")
    print("2. Test the installation:")
    print("   ./venv/bin/python -c 'import openpypi; print(openpypi.__version__)'")
    print("3. Run the CLI:")
    print("   ./venv/bin/openpypi --help")
    print("4. Start the API server:")
    print("   ./venv/bin/uvicorn openpypi.api.app:app --reload")
    print("5. For production deployment:")
    print("   - Set up GitHub secrets for PYPI_API_TOKEN")
    print("   - Push to main branch to trigger CI/CD")
    print("   - Tag a release to publish to PyPI")

def main():
    """Main setup function."""
    print("STARTING: OpenPypi complete setup...")
    
    # Check prerequisites
    check_python_version()
    
    # Setup environment
    pip_path, python_path = setup_environment()
    
    # Install dependencies
    install_dependencies(pip_path)
    
    # Create environment template
    create_env_template()
    
    # Run tests
    tests_passed = run_tests(python_path)
    
    # Run code quality checks
    quality_passed = run_code_quality_checks(python_path)
    
    # Build package
    build_success = build_package(python_path)
    
    # Print summary
    print("\nSUMMARY: Setup Summary:")
    print(f"  Tests: {'SUCCESS: Passed' if tests_passed else 'WARNING: Issues found'}")
    print(f"  Code Quality: {'SUCCESS: Passed' if quality_passed else 'WARNING: Issues found'}")
    print(f"  Package Build: {'SUCCESS: Success' if build_success else 'FAILED: Failed'}")
    
    if build_success:
        print_next_steps()
    else:
        print("FAILED: Setup completed with issues. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 