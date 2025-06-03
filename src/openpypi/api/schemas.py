"""
Pydantic models for OpenPypi API request and response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator


# Generic Response Models
class APIResponse(BaseModel):
    """Generic API response model."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorDetail(BaseModel):
    """Error detail model for API responses."""

    loc: Optional[List[Union[str, int]]] = None
    msg: str
    type: str


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = False
    error: str
    message: Optional[str] = None
    details: Optional[List[ErrorDetail]] = None


# Health Check Models
class HealthStatus(BaseModel):
    """Health status model."""

    status: str = "healthy"
    timestamp: datetime
    dependencies: Optional[Dict[str, str]] = None
    uptime_seconds: Optional[float] = None


# Project Generation Models
class ProjectRequest(BaseModel):
    """Request model for generating a project with direct parameters."""

    name: str = Field(..., min_length=1, description="The project name.")
    description: str = Field(..., min_length=1, description="Project description.")
    author: str = Field(..., min_length=1, description="Author's name.")
    email: EmailStr = Field(..., description="Author's email.")
    version: Optional[str] = Field(
        "0.1.0", pattern=r"^\d+\.\d+\.\d+([a-zA-Z0-9.-]*)$", description="Initial project version."
    )
    options: Optional[Dict[str, Any]] = Field(None, description="Additional project options.")

    # Project options (can also be specified in options dict)
    use_fastapi: Optional[bool] = Field(True, description="Include FastAPI integration.")
    use_docker: Optional[bool] = Field(True, description="Include Docker support.")
    use_openai: Optional[bool] = Field(True, description="Include OpenAI integration templates.")
    create_tests: Optional[bool] = Field(True, description="Generate a basic test suite.")
    initialize_git: Optional[bool] = Field(True, description="Initialize a Git repository.")
    test_framework: Optional[str] = Field("pytest", description="Test framework to use.")


class ProjectIdeaRequest(BaseModel):
    """Request model for generating a project from an idea."""

    idea: str = Field(
        ..., min_length=10, description="The core idea or description of the project."
    )
    package_name: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Desired package name (e.g., my_awesome_package).",
    )
    output_dir: Optional[str] = Field(
        None,
        description="Output directory for the generated project (server-side setting primarily).",
    )
    author: Optional[str] = Field("OpenPypi User", description="Author's name.")
    email: Optional[EmailStr] = Field("user@example.com", description="Author's email.")
    version: Optional[str] = Field(
        "0.1.0", pattern=r"^\d+\.\d+\.\d+([a-zA-Z0-9.-]*)$", description="Initial project version."
    )
    description: Optional[str] = Field(None, description="Short description of the project.")
    use_fastapi: bool = Field(True, description="Include FastAPI integration.")
    use_docker: bool = Field(True, description="Include Docker support.")
    use_openai: bool = Field(True, description="Include OpenAI integration templates.")
    create_tests: bool = Field(True, description="Generate a basic test suite.")
    initialize_git: bool = Field(True, description="Initialize a Git repository.")
    # Add more configuration options as needed
    # e.g., license_type, ci_cd_provider, cloud_provider, database_type etc.


class ProjectGenerationResult(BaseModel):
    """Result of a project generation operation."""

    package_name: str
    output_directory: str  # This might be a server path, consider how to present to client
    files_created: List[str]
    directories_created: List[str]
    pipeline_summary: Dict[str, Any]  # Summary of the generation pipeline execution


class GenerationResponse(APIResponse):
    """Response model for project generation."""

    data: Optional[ProjectGenerationResult] = None


# Project Management Models
class ProjectMetadata(BaseModel):
    """Metadata for a generated project."""

    package_name: str
    description: Optional[str] = None
    version: str
    author: Optional[str] = None
    created_at: datetime
    last_modified: datetime
    project_path: str  # Server-side path
    status: str  # e.g., 'generated', 'deployed', 'archived'
    # Add other relevant metadata fields


class ProjectListResponse(APIResponse):
    """Response model for listing projects."""

    data: List[ProjectMetadata]


# OpenAI Integration Models
class OpenAICompletionRequest(BaseModel):
    """Request model for OpenAI completion."""

    prompt: str = Field(..., description="Prompt to send to OpenAI.")
    model: str = Field(
        "text-davinci-003", description="OpenAI model to use."
    )  # Example, update as needed
    max_tokens: int = Field(150, gt=0, le=4000)
    temperature: float = Field(0.7, ge=0.0, le=1.0)


class OpenAICompletionResponse(APIResponse):
    """Response model for OpenAI completion."""

    data: Dict[str, Any]  # Raw OpenAI response or a structured subset


# Authentication Models
class Token(BaseModel):
    """Token model for authentication responses."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data model for token payload."""

    username: Optional[str] = None


class UserCreate(BaseModel):
    """User creation model for registration."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)


class User(BaseModel):
    """User model."""

    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    """User model as stored in DB (includes hashed password)."""

    hashed_password: str


# General Utility Schemas
class TaskStatus(BaseModel):
    """Schema for reporting the status of a background task."""

    task_id: str
    status: str = Field(..., description="e.g., PENDING, STARTED, SUCCESS, FAILURE, RETRY")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Percentage progress.")
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
