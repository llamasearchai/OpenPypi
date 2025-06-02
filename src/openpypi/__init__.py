"""
OpenPypi - Complete Python Project Generator.

A comprehensive tool for generating Python projects with FastAPI, Docker,
CI/CD, tests, and OpenAI integration.
"""

__version__ = "0.1.0"
__author__ = "OpenPypi Team"
__email__ = "team@openpypi.com"

from .core import Config, ProjectGenerator
from .core.exceptions import GenerationError, OpenPypiError, ValidationError

__all__ = [
    "ProjectGenerator",
    "Config",
    "OpenPypiError",
    "ValidationError",
    "GenerationError",
    "__version__",
]
