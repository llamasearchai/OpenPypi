#!/bin/bash
# Script to publish OpenPypi to PyPI

set -e

echo "Publishing OpenPypi to PyPI..."

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Update version if needed
echo "Current version in pyproject.toml:"
grep "^version" pyproject.toml

# Build the package
echo "Building package..."
python -m build

# Check the build
echo "Checking package..."
twine check dist/*

# Upload to PyPI
echo "Uploading to PyPI..."
echo "Please ensure you have your PyPI token ready."
echo "You can set it as TWINE_PASSWORD environment variable or enter it when prompted."

# Use token authentication
twine upload dist/* \
    --username __token__ \
    --verbose

echo "Publication complete!"
echo "View your package at: https://pypi.org/project/openpypi/" 