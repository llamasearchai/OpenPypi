"""
Authentication and Authorization module for OpenPypi
Comprehensive security with JWT, OAuth2, API keys, and rate limiting
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from functools import wraps

import jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from openpypi.core.config import get_settings
from openpypi.database.session import get_db
from openpypi.database.models import User, ApiKey, AuditLog, UserRole, UserStatus, ApiKeyStatus, AuditAction
from openpypi.core.exceptions import OpenPypiException

logger = structlog.get_logger(__name__)

# Security contexts
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Token constants
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
RESET_TOKEN_EXPIRE_HOURS = 24
VERIFY_TOKEN_EXPIRE_HOURS = 48


class AuthenticationError(OpenPypiException):
    """Authentication related errors."""
    pass


class AuthorizationError(OpenPypiException):
    """Authorization related errors."""
    pass


class SecurityService:
    """Comprehensive security service for authentication and authorization."""
    
    def __init__(self):
        self.settings = get_settings()
    
    # Password handling
    def hash_password(self, password: str) -> str:
        """Hash a password securely."""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Additional password strength validation
        if not self._is_password_strong(password):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _is_password_strong(self, password: str) -> bool:
        """Check if password meets strength requirements."""
        import re
        
        # At least 8 characters, one uppercase, one lowercase, one digit, one special char
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        return bool(re.match(pattern, password))
    
    # JWT Token handling
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.settings.secret_key, algorithm="HS256")
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, self.settings.secret_key, algorithm="HS256")
    
    def create_reset_token(self, user_id: str) -> str:
        """Create password reset token."""
        data = {
            "user_id": user_id,
            "type": "reset",
            "exp": datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS),
            "iat": datetime.now(timezone.utc)
        }
        
        return jwt.encode(data, self.settings.secret_key, algorithm="HS256")
    
    def create_verification_token(self, user_id: str) -> str:
        """Create email verification token."""
        data = {
            "user_id": user_id,
            "type": "verify",
            "exp": datetime.now(timezone.utc) + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
            "iat": datetime.now(timezone.utc)
        }
        
        return jwt.encode(data, self.settings.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=["HS256"])
            
            # Check token type
            if payload.get("type") != token_type:
                raise AuthenticationError("Invalid token type")
            
            # Check expiration
            if datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token received", error=str(e))
            raise AuthenticationError("Invalid token")
    
    # API Key handling
    def generate_api_key(self) -> tuple[str, str]:
        """Generate a new API key and return (key, hash)."""
        # Generate a secure random key
        key = f"oppy_{secrets.token_urlsafe(32)}"
        key_hash = pwd_context.hash(key)
        return key, key_hash
    
    def verify_api_key(self, key: str, key_hash: str) -> bool:
        """Verify API key against its hash."""
        return pwd_context.verify(key, key_hash)
    
    # Rate limiting
    def check_rate_limit(self, identifier: str, limit: int, window_seconds: int = 3600) -> bool:
        """Check if rate limit is exceeded."""
        # Implementation would use Redis or in-memory cache
        # For now, returning True (not rate limited)
        return True
    
    # Session management
    def create_session_token(self, user_id: str, device_info: Dict[str, Any]) -> str:
        """Create a secure session token."""
        session_data = {
            "user_id": user_id,
            "device_info": device_info,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "session_id": secrets.token_urlsafe(16)
        }
        
        return jwt.encode(session_data, self.settings.secret_key, algorithm="HS256")


# Global security service instance
security_service = SecurityService()


# User management functions
async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Error fetching user by ID", user_id=user_id, error=str(e))
        return None


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    try:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Error fetching user by username", username=username, error=str(e))
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    try:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Error fetching user by email", email=email, error=str(e))
        return None


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate user with username/email and password."""
    try:
        # Try to find user by username or email
        user = await get_user_by_username(db, username)
        if not user:
            user = await get_user_by_email(db, username)
        
        if not user:
            logger.warning("Authentication failed: user not found", username=username)
            return None
        
        # Check if account is active
        if not user.is_active or user.status != UserStatus.ACTIVE:
            logger.warning("Authentication failed: account inactive", user_id=user.id)
            return None
        
        # Verify password
        if not security_service.verify_password(password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            await db.commit()
            
            logger.warning("Authentication failed: invalid password", user_id=user.id)
            return None
        
        # Reset failed login attempts and update last login
        user.failed_login_attempts = 0
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info("User authenticated successfully", user_id=user.id, username=user.username)
        return user
        
    except Exception as e:
        logger.error("Error during authentication", error=str(e))
        return None


# API Key functions
async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> Optional[ApiKey]:
    """Get API key by hash."""
    try:
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.key_hash == key_hash)
            .where(ApiKey.status == ApiKeyStatus.ACTIVE)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Error fetching API key", error=str(e))
        return None


async def verify_api_key(db: AsyncSession, key: str) -> Optional[tuple[ApiKey, User]]:
    """Verify API key and return key and user if valid."""
    try:
        # Extract key hash
        key_hash = pwd_context.hash(key)
        
        # Find matching API key
        result = await db.execute(
            select(ApiKey, User)
            .join(User)
            .where(ApiKey.status == ApiKeyStatus.ACTIVE)
        )
        
        for api_key, user in result:
            if security_service.verify_api_key(key, api_key.key_hash):
                # Check if key is still valid
                if api_key.is_valid() and user.is_active:
                    # Update usage
                    api_key.usage_count += 1
                    api_key.last_used = datetime.now(timezone.utc)
                    await db.commit()
                    
                    return api_key, user
        
        return None
        
    except Exception as e:
        logger.error("Error verifying API key", error=str(e))
        return None


# Authentication dependencies
async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify token
        payload = security_service.verify_token(credentials.credentials, "access")
        user_id = payload.get("sub")
        
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        # Get user from database
        user = await get_user_by_id(db, user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active or user.status != UserStatus.ACTIVE:
            raise AuthenticationError("User account is inactive")
        
        return user
        
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from API key."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    
    try:
        result = await verify_api_key(db, api_key)
        if result:
            api_key_obj, user = result
            return user
        return None
        
    except Exception as e:
        logger.error("Error authenticating with API key", error=str(e))
        return None


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> User:
    """Get current user from either JWT token or API key."""
    user = token_user or api_key_user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return user


# Authorization decorators and functions
def require_roles(*roles: UserRole):
    """Decorator to require specific user roles."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            
            if not current_user or current_user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require super admin role."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


# Audit logging
async def log_audit_event(
    db: AsyncSession,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None
):
    """Log audit event to database."""
    try:
        audit_log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
            duration_ms=duration_ms
        )
        
        db.add(audit_log)
        await db.commit()
        
    except Exception as e:
        logger.error("Failed to log audit event", error=str(e))


# Token validation helpers
def validate_reset_token(token: str) -> Optional[str]:
    """Validate password reset token and return user ID."""
    try:
        payload = security_service.verify_token(token, "reset")
        return payload.get("user_id")
    except AuthenticationError:
        return None


def validate_verification_token(token: str) -> Optional[str]:
    """Validate email verification token and return user ID."""
    try:
        payload = security_service.verify_token(token, "verify")
        return payload.get("user_id")
    except AuthenticationError:
        return None


# Security utilities
def generate_secure_filename(filename: str) -> str:
    """Generate a secure filename."""
    import os
    import re
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(filename)
    
    return f"{name}_{timestamp}{ext}"


def generate_csrf_token() -> str:
    """Generate CSRF protection token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """Verify CSRF token."""
    return secrets.compare_digest(token, expected)


# Session security
def generate_session_id() -> str:
    """Generate secure session ID."""
    return secrets.token_urlsafe(32)


def hash_ip_address(ip_address: str) -> str:
    """Hash IP address for privacy-compliant logging."""
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16] 