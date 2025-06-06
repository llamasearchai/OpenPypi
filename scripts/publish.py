#!/usr/bin/env python3
"""
OpenPypi Publishing Script

This script handles building and publishing the OpenPypi package to PyPI.
It includes comprehensive checks, testing, and publishing workflow.

Usage:
    python scripts/publish.py --help
    python scripts/publish.py check
    python scripts/publish.py build
    python scripts/publish.py test-publish
    python scripts/publish.py publish
"""

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_command(
    cmd: List[str], cwd: Optional[Path] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_version() -> str:
    """Get the current package version."""
    try:
        return importlib.metadata.version("openpypi")
    except importlib.metadata.PackageNotFoundError:
        # If not installed, try to read from _version.py
        version_file = get_project_root() / "src" / "openpypi" / "_version.py"
        if version_file.exists():
            with open(version_file) as f:
                for line in f:
                    if line.startswith("__version__"):
                        return line.split("=")[1].strip().strip("\"'")
        return "1.0.0"


def check_environment() -> Dict[str, Any]:
    """Check the development environment."""
    print("CHECKING: Checking development environment...")

    checks = {
        "python_version": sys.version,
        "working_directory": str(get_project_root()),
        "git_status": None,
        "dependencies": {},
        "test_status": None,
        "lint_status": None,
        "security_status": None,
    }

    # Check Git status
    try:
        result = run_command(["git", "status", "--porcelain"], check=False)
        if result.returncode == 0:
            checks["git_status"] = "clean" if not result.stdout.strip() else "dirty"
        else:
            checks["git_status"] = "error"
    except FileNotFoundError:
        checks["git_status"] = "git_not_found"

    # Check required dependencies
    required_deps = ["build", "twine", "pytest", "black", "isort", "flake8", "pylint", "mypy"]
    for dep in required_deps:
        try:
            version = importlib.metadata.version(dep)
            checks["dependencies"][dep] = version
        except importlib.metadata.PackageNotFoundError:
            checks["dependencies"][dep] = "not_installed"

    return checks


def run_tests() -> bool:
    """Run the test suite."""
    print("TESTING: Running test suite...")

    project_root = get_project_root()

    # Run tests with coverage
    result = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=openpypi",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "tests/",
        ],
        cwd=project_root,
        check=False,
    )

    return result.returncode == 0


def run_linting() -> bool:
    """Run code linting and formatting checks."""
    print("LINTING: Running linting and formatting checks...")

    project_root = get_project_root()
    success = True

    # Check black formatting
    result = run_command(
        [sys.executable, "-m", "black", "--check", "--diff", "src", "tests"],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        success = False
        print("FAILED: Black formatting check failed")

    # Check isort
    result = run_command(
        [sys.executable, "-m", "isort", "--check-only", "--diff", "src", "tests"],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        success = False
        print("FAILED: isort check failed")

    # Run flake8
    result = run_command(
        [sys.executable, "-m", "flake8", "src", "tests"], cwd=project_root, check=False
    )
    if result.returncode != 0:
        success = False
        print("FAILED: flake8 check failed")

    # Run pylint
    result = run_command([sys.executable, "-m", "pylint", "src"], cwd=project_root, check=False)
    if result.returncode not in [0, 28]:  # 28 is warning level
        success = False
        print("FAILED: pylint check failed")

    # Run mypy
    result = run_command([sys.executable, "-m", "mypy", "src"], cwd=project_root, check=False)
    if result.returncode != 0:
        success = False
        print("FAILED: mypy check failed")

    return success


def run_security_checks() -> bool:
    """Run security checks."""
    print("SECURITY: Running security checks...")

    project_root = get_project_root()
    success = True

    # Run bandit
    result = run_command(
        [sys.executable, "-m", "bandit", "-r", "src", "-f", "json", "-o", "bandit-report.json"],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        success = False
        print("FAILED: bandit security check failed")

    # Run safety
    result = run_command(
        [sys.executable, "-m", "safety", "check", "--json", "--output", "safety-report.json"],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        success = False
        print("FAILED: safety security check failed")

    return success


def build_package() -> bool:
    """Build the package distribution."""
    print("BUILDING: Building package...")

    project_root = get_project_root()

    # Clean previous builds
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Build package
    result = run_command([sys.executable, "-m", "build"], cwd=project_root, check=False)

    if result.returncode != 0:
        print("FAILED: Package build failed")
        return False

    # Check built package
    result = run_command(
        [sys.executable, "-m", "twine", "check", "dist/*"], cwd=project_root, check=False
    )

    if result.returncode != 0:
        print("FAILED: Package validation failed")
        return False

    print("SUCCESS: Package built successfully")
    return True


def publish_test() -> bool:
    """Publish to TestPyPI."""
    print("PUBLISHING: Publishing to TestPyPI...")

    project_root = get_project_root()

    # Check for TestPyPI token
    if not os.getenv("TEST_PYPI_TOKEN"):
        print("FAILED: TEST_PYPI_TOKEN environment variable not set")
        print("   Get a token from https://test.pypi.org/manage/account/token/")
        return False

    result = run_command(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository",
            "testpypi",
            "--username",
            "__token__",
            "--password",
            os.getenv("TEST_PYPI_TOKEN"),
            "dist/*",
        ],
        cwd=project_root,
        check=False,
    )

    if result.returncode != 0:
        print("FAILED: TestPyPI upload failed")
        return False

    print("SUCCESS: Successfully published to TestPyPI")
    print(
        f"   Test installation: pip install -i https://test.pypi.org/simple/ openpypi=={get_version()}"
    )
    return True


def publish_pypi() -> bool:
    """Publish to PyPI."""
    print("PUBLISHING: Publishing to PyPI...")

    project_root = get_project_root()

    # Check for PyPI token
    if not os.getenv("PYPI_TOKEN"):
        print("FAILED: PYPI_TOKEN environment variable not set")
        print("   Get a token from https://pypi.org/manage/account/token/")
        return False

    # Confirm publication
    version = get_version()
    response = input(f"Are you sure you want to publish openpypi v{version} to PyPI? (yes/no): ")
    if response.lower() != "yes":
        print("CANCELLED: Publication cancelled")
        return False

    result = run_command(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--username",
            "__token__",
            "--password",
            os.getenv("PYPI_TOKEN"),
            "dist/*",
        ],
        cwd=project_root,
        check=False,
    )

    if result.returncode != 0:
        print("FAILED: PyPI upload failed")
        return False

    print("SUCCESS: Successfully published to PyPI")
    print(f"   Installation: pip install openpypi=={version}")
    print(f"   PyPI page: https://pypi.org/project/openpypi/{version}/")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenPypi Publishing Script")
    parser.add_argument(
        "command",
        choices=["check", "test", "lint", "security", "build", "test-publish", "publish", "full"],
        help="Command to run",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-lint", action="store_true", help="Skip linting checks")
    parser.add_argument("--skip-security", action="store_true", help="Skip security checks")
    parser.add_argument(
        "--force", action="store_true", help="Force publication even if checks fail"
    )

    args = parser.parse_args()

    print(f"STARTING: OpenPypi Publishing Script v{get_version()}")
    print("=" * 50)

    if args.command == "check":
        checks = check_environment()
        print("\nREPORT: Environment Check Results:")
        print(f"Python Version: {checks['python_version']}")
        print(f"Working Directory: {checks['working_directory']}")
        print(f"Git Status: {checks['git_status']}")

        print("\nDependencies:")
        for dep, version in checks["dependencies"].items():
            status = "AVAILABLE" if version != "not_installed" else "MISSING"
            print(f"  {status} {dep}: {version}")

        return 0

    elif args.command == "test":
        success = run_tests()
        return 0 if success else 1

    elif args.command == "lint":
        success = run_linting()
        return 0 if success else 1

    elif args.command == "security":
        success = run_security_checks()
        return 0 if success else 1

    elif args.command == "build":
        success = build_package()
        return 0 if success else 1

    elif args.command == "test-publish":
        if not build_package():
            return 1
        success = publish_test()
        return 0 if success else 1

    elif args.command == "publish":
        if not build_package():
            return 1
        success = publish_pypi()
        return 0 if success else 1

    elif args.command == "full":
        # Full publishing workflow
        success = True

        # Run all checks
        if not args.skip_tests:
            success &= run_tests()

        if not args.skip_lint:
            success &= run_linting()

        if not args.skip_security:
            success &= run_security_checks()

        if not success and not args.force:
            print("FAILED: Checks failed. Use --force to ignore.")
            return 1

        # Build package
        if not build_package():
            return 1

        # Publish to TestPyPI first
        if not publish_test():
            return 1

        # Ask to continue to PyPI
        response = input("Continue to publish to PyPI? (yes/no): ")
        if response.lower() == "yes":
            success = publish_pypi()
            return 0 if success else 1

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
