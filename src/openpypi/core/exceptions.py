"""
Custom exceptions for OpenPypi.
"""


class OpenPypiError(Exception):
    """Base exception for OpenPypi errors."""

    pass


class ValidationError(OpenPypiError):
    """Raised when validation fails."""

    pass


class GenerationError(OpenPypiError):
    """Raised when project generation fails."""

    pass


class ConfigurationError(OpenPypiError):
    """Raised when configuration is invalid."""

    pass


class TemplateError(OpenPypiError):
    """Raised when template processing fails."""

    pass


class DependencyError(OpenPypiError):
    """Raised when dependency resolution fails."""

    pass


class ProviderError(OpenPypiError):
    """Raised when provider operations fail."""

    pass


class StageError(OpenPypiError):
    """Raised when stage execution fails."""

    pass
