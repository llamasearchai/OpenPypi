"""
SQLAlchemy models for OpenPypi
Comprehensive database models with security, validation, and proper relationships
"""

import secrets
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

import structlog
from passlib.context import CryptContext
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin to add timestamp fields to models."""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDMixin:
    """Mixin to add UUID primary key to models."""

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)


# Enums
class UserRole(PyEnum):
    """User roles for access control."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(PyEnum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class ProjectStatus(PyEnum):
    """Project status."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    DRAFT = "draft"


class PackageStatus(PyEnum):
    """Package status."""

    PENDING = "pending"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"
    PUBLISHED = "published"


class ApiKeyStatus(PyEnum):
    """API key status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class AuditAction(PyEnum):
    """Audit log actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    API_CALL = "api_call"
    PUBLISH = "publish"
    DOWNLOAD = "download"


# Models
class User(Base, UUIDMixin, TimestampMixin):
    """User model with comprehensive security features."""

    __tablename__ = "users"

    # Basic information
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)

    # Security
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)

    # Settings
    preferences = Column(JSON, default=dict, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(username) >= 3", name="username_min_length"),
        CheckConstraint("LENGTH(username) <= 50", name="username_max_length"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", name="valid_email"
        ),
        Index("idx_user_username_email", "username", "email"),
        Index("idx_user_status_active", "status", "is_active"),
    )

    def set_password(self, password: str) -> None:
        """Hash and set password securely."""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, self.hashed_password)

    def generate_verification_token(self) -> str:
        """Generate email verification token."""
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token

    def generate_password_reset_token(self) -> str:
        """Generate password reset token."""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.now(timezone.utc).replace(hours=24)  # 24 hours
        return self.password_reset_token

    def is_password_reset_valid(self) -> bool:
        """Check if password reset token is still valid."""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        return datetime.now(timezone.utc) < self.password_reset_expires

    @validates("email")
    def validate_email(self, key, email):
        """Validate email format."""
        import re

        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        return email.lower()

    @validates("username")
    def validate_username(self, key, username):
        """Validate username format."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]{3,50}$", username):
            raise ValueError(
                "Username must be 3-50 characters and contain only letters, numbers, underscore, or dash"
            )
        return username.lower()

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email if include_sensitive else None,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role.value,
            "status": self.status.value,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "website": self.website,
            "location": self.location,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

        if not include_sensitive:
            # Remove sensitive fields for public view
            data.pop("email", None)

        return data


class Project(Base, UUIDMixin, TimestampMixin):
    """Project model for tracking generated packages."""

    __tablename__ = "projects"

    # Basic information
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(20), default="0.1.0", nullable=False)

    # Project details
    author = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    license = Column(String(50), default="MIT", nullable=False)
    python_version = Column(String(20), default=">=3.9", nullable=False)

    # Status and metadata
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    star_count = Column(Integer, default=0, nullable=False)

    # Configuration
    config = Column(JSON, default=dict, nullable=False)
    requirements = Column(JSON, default=list, nullable=False)
    keywords = Column(JSON, default=list, nullable=False)
    classifiers = Column(JSON, default=list, nullable=False)

    # Repository information
    repository_url = Column(String(500), nullable=True)
    homepage_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)

    # Generation metadata
    generated_with_ai = Column(Boolean, default=True, nullable=False)
    generation_prompt = Column(Text, nullable=True)
    generation_model = Column(String(100), nullable=True)

    # Foreign keys
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="projects")
    packages = relationship("Package", back_populates="project", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name="unique_project_per_user"),
        CheckConstraint("LENGTH(name) >= 3", name="project_name_min_length"),
        CheckConstraint("LENGTH(name) <= 100", name="project_name_max_length"),
        CheckConstraint("download_count >= 0", name="positive_download_count"),
        CheckConstraint("star_count >= 0", name="positive_star_count"),
        Index("idx_project_name_status", "name", "status"),
        Index("idx_project_owner_status", "owner_id", "status"),
        Index("idx_project_public", "is_public", "status"),
    )

    @validates("name")
    def validate_name(self, key, name):
        """Validate project name format."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]{3,100}$", name):
            raise ValueError(
                "Project name must be 3-100 characters and contain only letters, numbers, underscore, or dash"
            )
        return name.lower().replace("_", "-")

    @validates("version")
    def validate_version(self, key, version):
        """Validate semantic version format."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9-]+)?(?:\+[a-zA-Z0-9-]+)?$", version):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return version

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert project to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "author_email": self.author_email,
            "license": self.license,
            "python_version": self.python_version,
            "status": self.status.value,
            "is_public": self.is_public,
            "download_count": self.download_count,
            "star_count": self.star_count,
            "requirements": self.requirements,
            "keywords": self.keywords,
            "classifiers": self.classifiers,
            "repository_url": self.repository_url,
            "homepage_url": self.homepage_url,
            "documentation_url": self.documentation_url,
            "generated_with_ai": self.generated_with_ai,
            "generation_model": self.generation_model,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "owner": self.owner.to_dict() if self.owner else None,
        }


class Package(Base, UUIDMixin, TimestampMixin):
    """Package build and publishing tracking."""

    __tablename__ = "packages"

    # Basic information
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    status = Column(Enum(PackageStatus), default=PackageStatus.PENDING, nullable=False)

    # Build information
    build_log = Column(Text, nullable=True)
    build_duration = Column(Float, nullable=True)  # seconds
    file_size = Column(Integer, nullable=True)  # bytes
    file_hash = Column(String(64), nullable=True)  # SHA256

    # Publishing information
    pypi_url = Column(String(500), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    downloads = Column(Integer, default=0, nullable=False)

    # Error information
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Foreign keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="packages")

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "version", name="unique_package_version"),
        CheckConstraint("downloads >= 0", name="positive_downloads"),
        CheckConstraint("file_size >= 0", name="positive_file_size"),
        CheckConstraint("build_duration >= 0", name="positive_build_duration"),
        Index("idx_package_name_version", "name", "version"),
        Index("idx_package_status", "status"),
        Index("idx_package_project", "project_id", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert package to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "build_duration": self.build_duration,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "pypi_url": self.pypi_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "downloads": self.downloads,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "project_id": self.project_id,
        }


class ApiKey(Base, UUIDMixin, TimestampMixin):
    """API key management for secure access."""

    __tablename__ = "api_keys"

    # Key information
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    prefix = Column(String(10), nullable=False)  # First few characters for identification

    # Status and permissions
    status = Column(Enum(ApiKeyStatus), default=ApiKeyStatus.ACTIVE, nullable=False)
    scopes = Column(JSON, default=list, nullable=False)  # List of permitted scopes
    rate_limit = Column(Integer, default=1000, nullable=False)  # Requests per hour

    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Constraints
    __table_args__ = (
        CheckConstraint("rate_limit > 0", name="positive_rate_limit"),
        CheckConstraint("usage_count >= 0", name="positive_usage_count"),
        Index("idx_apikey_user_status", "user_id", "status"),
        Index("idx_apikey_hash", "key_hash"),
    )

    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """Generate a new API key and return (key, hash)."""
        key = f"oppy_{secrets.token_urlsafe(32)}"
        key_hash = pwd_context.hash(key)
        return key, key_hash

    def verify_key(self, key: str) -> bool:
        """Verify API key against hash."""
        return pwd_context.verify(key, self.key_hash)

    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if API key is valid for use."""
        return self.status == ApiKeyStatus.ACTIVE and not self.is_expired()

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert API key to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "status": self.status.value,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
        }


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Comprehensive audit logging for security and compliance."""

    __tablename__ = "audit_logs"

    # Action information
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)  # e.g., "user", "project", "package"
    resource_id = Column(String(36), nullable=True)

    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    endpoint = Column(String(200), nullable=True)
    method = Column(String(10), nullable=True)

    # Result information
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)

    # Additional metadata
    extra_data = Column(JSON, default=dict, nullable=False)
    duration_ms = Column(Float, nullable=True)

    # Foreign keys
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Constraints
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_timestamp", "created_at"),
        Index("idx_audit_ip", "ip_address"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            "id": self.id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "success": self.success,
            "error_message": self.error_message,
            "extra_data": self.extra_data,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
        }


# Database initialization functions
def create_tables(engine):
    """Create all tables in the database."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


def drop_tables(engine):
    """Drop all tables in the database."""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error("Failed to drop database tables", error=str(e))
        raise
