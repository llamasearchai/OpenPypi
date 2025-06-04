"""
Custom exceptions for OpenPypi.
"""


class OpenPypiException(Exception):
    """Base exception for OpenPypi."""

    pass


class ValidationError(OpenPypiException):
    """Raised when validation fails."""

    pass


class GenerationError(OpenPypiException):
    """Raised when project generation fails."""

    pass


class ConfigurationError(OpenPypiException):
    """Raised when configuration is invalid."""

    pass


class TemplateError(OpenPypiException):
    """Raised when template processing fails."""

    pass


class DependencyError(OpenPypiException):
    """Raised when dependency resolution fails."""

    pass


class ProviderError(OpenPypiException):
    """Raised when provider operations fail."""

    pass


class StageError(OpenPypiException):
    """Raised when stage execution fails."""

    pass


class AuthenticationError(OpenPypiException):
    """Raised when authentication fails."""

    pass


class AuthorizationError(OpenPypiException):
    """Raised when authorization fails."""

    pass
