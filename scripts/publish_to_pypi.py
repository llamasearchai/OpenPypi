#!/usr/bin/env python3
"""
Secure PyPI publishing script for OpenPypi.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def load_environment():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print("SUCCESS: Loaded environment from .env file")
    else:
        print("WARNING: No .env file found, using system environment variables")


def check_prerequisites():
    """Check if all prerequisites are met for publishing."""
    print("CHECKING: Checking prerequisites...")

    # Check if we have the PyPI token
    pypi_token = os.getenv("PYPI_API_TOKEN")
    if not pypi_token:
        print("FAILED: PYPI_API_TOKEN not found in environment variables")
        print("   Please add your PyPI API token to the .env file")
        print("   Get your token from: https://pypi.org/manage/account/token/")
        return False

    # Check if distribution files exist
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("FAILED: dist/ directory not found")
        print("   Please run: python -m build")
        return False

    dist_files = list(dist_dir.glob("*"))
    if not dist_files:
        print("FAILED: No distribution files found in dist/")
        print("   Please run: python -m build")
        return False

    print(f"SUCCESS: Found {len(dist_files)} distribution files:")
    for file in dist_files:
        print(f"   PACKAGE: {file.name}")

    # Check if twine is installed
    try:
        subprocess.run(["twine", "--version"], check=True, capture_output=True)
        print("SUCCESS: twine is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("FAILED: twine not found")
        print("   Please install: pip install twine")
        return False

    return True


def run_security_checks():
    """Run security checks before publishing."""
    print("SECURITY: Running security checks...")

    checks_passed = True

    # Check for common security issues
    security_files = [".env", "*.key", "*.pem", "credentials.json"]

    for pattern in security_files:
        for file in Path(".").rglob(pattern):
            if file.is_file() and "dist" not in str(file):
                print(f"WARNING:  Security file found: {file}")
                print("   Ensure this file is in .gitignore and not included in the package")

    # Check if .env is properly ignored
    gitignore = Path(".gitignore")
    if gitignore.exists():
        gitignore_content = gitignore.read_text()
        if ".env" not in gitignore_content:
            print("WARNING:  .env not found in .gitignore")
            checks_passed = False

    return checks_passed


def validate_package():
    """Validate the package before publishing."""
    print("CHECKING: Validating package...")

    try:
        # Check package with twine
        result = subprocess.run(
            ["twine", "check", "dist/*"], check=True, capture_output=True, text=True
        )
        print("SUCCESS: Package validation passed")
        return True
    except subprocess.CalledProcessError as e:
        print("FAILED: Package validation failed:")
        print(e.stdout)
        print(e.stderr)
        return False


def publish_to_test_pypi():
    """Publish to Test PyPI first."""
    print("TESTING: Publishing to Test PyPI...")

    try:
        # Use test PyPI
        result = subprocess.run(
            [
                "twine",
                "upload",
                "--repository",
                "testpypi",
                "--username",
                "__token__",
                "--password",
                os.getenv("PYPI_API_TOKEN"),
                "dist/*",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print("SUCCESS: Successfully published to Test PyPI")
        print("URL: Check your package at: https://test.pypi.org/project/openpypi/")
        return True

    except subprocess.CalledProcessError as e:
        print("FAILED: Test PyPI publication failed:")
        print(e.stdout)
        print(e.stderr)
        return False


def publish_to_pypi():
    """Publish to the main PyPI."""
    print("PUBLISHING: Publishing to PyPI...")

    # Confirm publication
    response = input("Are you sure you want to publish to PyPI? (yes/no): ")
    if response.lower() != "yes":
        print("FAILED: Publication cancelled")
        return False

    try:
        result = subprocess.run(
            [
                "twine",
                "upload",
                "--username",
                "__token__",
                "--password",
                os.getenv("PYPI_API_TOKEN"),
                "dist/*",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print("SUCCESS: Successfully published to PyPI!")
        print("URL: Check your package at: https://pypi.org/project/openpypi/")
        return True

    except subprocess.CalledProcessError as e:
        print("FAILED: PyPI publication failed:")
        print(e.stdout)
        print(e.stderr)
        return False


def cleanup_build_artifacts():
    """Clean up build artifacts."""
    print("🧹 Cleaning up build artifacts...")

    import shutil

    artifacts = ["build", "*.egg-info"]
    for pattern in artifacts:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"   Removed {path}")


def main():
    """Main publishing function."""
    print("PUBLISHING: Starting PyPI publication process...")

    # Load environment
    load_environment()

    # Check prerequisites
    if not check_prerequisites():
        print("FAILED: Prerequisites not met. Please fix the issues above.")
        sys.exit(1)

    # Run security checks
    if not run_security_checks():
        response = input("Security issues found. Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            print("FAILED: Publication cancelled due to security concerns")
            sys.exit(1)

    # Validate package
    if not validate_package():
        print("FAILED: Package validation failed. Please fix the issues.")
        sys.exit(1)

    # Ask which PyPI to publish to
    print("\nREPORT: Publication options:")
    print("1. Test PyPI (recommended for testing)")
    print("2. Main PyPI (production)")
    print("3. Both (Test PyPI first, then main)")

    choice = input("Choose option (1-3): ").strip()

    success = False

    if choice in ["1", "3"]:
        success = publish_to_test_pypi()
        if not success and choice == "3":
            print("FAILED: Test PyPI publication failed. Skipping main PyPI.")
            sys.exit(1)

    if choice in ["2", "3"]:
        if choice == "3":
            input("Press Enter to continue to main PyPI (after testing on Test PyPI)...")
        success = publish_to_pypi()

    if success:
        print("\nSUCCESS: Publication completed successfully!")
        print("\nREPORT: Next steps:")
        print("1. Test the published package:")
        print("   pip install openpypi")
        print("2. Update documentation with new version")
        print("3. Create a GitHub release")
        print("4. Announce the release")

        # Clean up
        cleanup_build_artifacts()
    else:
        print("FAILED: Publication failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
