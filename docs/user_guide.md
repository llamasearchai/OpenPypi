# OpenPypi User Guide

## Table of Contents
1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Creating Projects](#creating-projects)
4. [Publishing to PyPI](#publishing-to-pypi)
5. [Provider Configuration](#provider-configuration)
6. [Advanced Features](#advanced-features)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

## Installation

### From PyPI
```bash
pip install openpypi
```

### From Source
```bash
git clone https://github.com/yourusername/openpypi.git
cd openpypi
pip install -e .[dev]
```

## Quick Start

### Create Your First Project
```bash
# Basic project
openpypi create my-awesome-package

# With all features
openpypi create my-api-project \
    --use-fastapi \
    --use-docker \
    --use-openai \
    --create-tests \
    --author "Your Name" \
    --email "your.email@example.com"
```

### Publish to PyPI
```bash
# Set your PyPI token
export PYPI_TOKEN="your-token-here"

# Publish your package
openpypi publish ./my-awesome-package
```

## Creating Projects

### Basic Usage
```bash
openpypi create project-name [options]
```

### Available Options
- `--package-name`: Override package name (default: project name with underscores)
- `--author`: Author name
- `--email`: Author email
- `--description`: Project description
- `--output-dir`: Output directory (default: current directory)
- `--use-fastapi`: Enable FastAPI integration
- `--use-openai`: Enable OpenAI integration
- `--use-docker`: Enable Docker support
- `--use-github-actions`: Enable GitHub Actions
- `--create-tests`: Generate test files
- `--use-git`: Initialize git repository
- `--test-framework`: Choose test framework (pytest/unittest)
- `--license`: License type (default: MIT)
- `--python-requires`: Python version requirement

### Project Structure 