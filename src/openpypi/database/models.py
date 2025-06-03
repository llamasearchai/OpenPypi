"""
Database models for OpenPypi using SQLAlchemy.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class TaskStatus(enum.Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectType(enum.Enum):
    """Project type enumeration."""

    BASIC = "basic"
    FASTAPI = "fastapi"
    CLI = "cli"
    LIBRARY = "library"
    MICROSERVICE = "microservice"


class AuditAction(enum.Enum):
    """Audit action enumeration."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    GENERATE = "generate"
    DOWNLOAD = "download"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Profile information
    bio = Column(Text)
    avatar_url = Column(String(500))
    github_username = Column(String(100))
    website = Column(String(500))

    # Usage tracking
    projects_count = Column(Integer, default=0, nullable=False)
    total_generations = Column(Integer, default=0, nullable=False)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    generation_tasks = relationship("GenerationTask", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

    @validates("email")
    def validate_email(self, key, email):
        """Validate email format."""
        import re

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError("Invalid email format")
        return email.lower()

    @validates("username")
    def validate_username(self, key, username):
        """Validate username format."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return username.lower()


class ApiKey(Base):
    """API key model for authentication."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Permissions and limits
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit = Column(Integer, default=1000)  # requests per hour
    scopes = Column(JSON, default=list)  # List of allowed scopes

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(name='{self.name}', user='{self.user.username if self.user else None}')>"

    @property
    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)


class Project(Base):
    """Project model for generated projects."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Project metadata
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.BASIC, nullable=False)
    package_name = Column(String(255), nullable=False)
    version = Column(String(50), default="0.1.0", nullable=False)
    author = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    license = Column(String(50), default="MIT", nullable=False)

    # Generation configuration
    config = Column(JSON, default=dict, nullable=False)

    # File tracking
    file_count = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(Integer, default=0, nullable=False)

    # Status and timestamps
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Download tracking
    download_count = Column(Integer, default=0, nullable=False)
    last_downloaded = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="projects")
    generation_tasks = relationship("GenerationTask", back_populates="project")

    # Indexes
    __table_args__ = (
        Index("idx_projects_user_name", "user_id", "name"),
        Index("idx_projects_created", "created_at"),
        Index("idx_projects_public", "is_public"),
    )

    def __repr__(self):
        return f"<Project(name='{self.name}', user='{self.user.username if self.user else None}')>"

    @validates("package_name")
    def validate_package_name(self, key, package_name):
        """Validate package name format."""
        import re

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", package_name):
            raise ValueError(
                "Package name must start with a letter and contain only letters, numbers, and underscores"
            )
        return package_name.lower()


class GenerationTask(Base):
    """Task model for tracking project generation."""

    __tablename__ = "generation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True)  # External task ID
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Task details
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    task_type = Column(String(50), default="project_generation", nullable=False)

    # Configuration and inputs
    input_data = Column(JSON, default=dict, nullable=False)
    configuration = Column(JSON, default=dict, nullable=False)

    # Results and outputs
    result_data = Column(JSON, default=dict)
    error_message = Column(Text)
    log_messages = Column(JSON, default=list)  # List of log entries

    # Progress tracking
    progress_percentage = Column(Integer, default=0, nullable=False)
    current_stage = Column(String(100))
    total_stages = Column(Integer, default=1, nullable=False)

    # Performance metrics
    execution_time_seconds = Column(Integer)
    memory_usage_mb = Column(Integer)
    cpu_usage_percent = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="generation_tasks")
    project = relationship("Project", back_populates="generation_tasks")

    # Indexes
    __table_args__ = (
        Index("idx_tasks_user_status", "user_id", "status"),
        Index("idx_tasks_created", "created_at"),
        Index("idx_tasks_status", "status"),
    )

    def __repr__(self):
        return f"<GenerationTask(task_id='{self.task_id}', status='{self.status.value}')>"

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate task duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return int((self.completed_at - self.started_at).total_seconds())

    @property
    def is_finished(self) -> bool:
        """Check if task is in a finished state."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]


class AuditLog(Base):
    """Audit log model for tracking user actions."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Action details
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255))

    # Request details
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(Text)
    request_id = Column(String(255))

    # Additional data
    details = Column(JSON, default=dict)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_ip", "ip_address"),
    )

    def __repr__(self):
        return f"<AuditLog(action='{self.action.value}', resource='{self.resource_type}')>"


class SystemMetric(Base):
    """System metrics model for monitoring."""

    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric details
    metric_type = Column(String(100), nullable=False)
    metric_name = Column(String(255), nullable=False)
    value = Column(String(255), nullable=False)  # Store as string for flexibility
    unit = Column(String(50))

    # Metadata
    tags = Column(JSON, default=dict)
    hostname = Column(String(255))

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_metrics_type_name", "metric_type", "metric_name"),
        Index("idx_metrics_timestamp", "timestamp"),
        UniqueConstraint(
            "metric_type", "metric_name", "hostname", "timestamp", name="uq_metric_per_host_time"
        ),
    )

    def __repr__(self):
        return f"<SystemMetric(type='{self.metric_type}', name='{self.metric_name}', value='{self.value}')>"


class Configuration(Base):
    """Configuration model for system settings."""

    __tablename__ = "configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Configuration details
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)

    # Metadata
    category = Column(String(100), default="general", nullable=False)
    is_secret = Column(Boolean, default=False, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes
    __table_args__ = (Index("idx_config_category", "category"),)

    def __repr__(self):
        return f"<Configuration(key='{self.key}', category='{self.category}')>"
