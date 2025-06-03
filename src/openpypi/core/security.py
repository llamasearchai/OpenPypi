"""
Core security utilities for OpenPypi (Passwords, JWT Tokens).
Production-ready implementation using bcrypt and PyJWT.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Configuration
SECRET_KEY = os.environ.get("API_SECRET_KEY", "a_very_secret_key_that_should_be_in_env_or_config")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class UserInDB:
    """User model for DB representation (used in auth routes)."""

    def __init__(
        self,
        username: str,
        email: Optional[str],
        full_name: Optional[str],
        hashed_password: str,
        disabled: Optional[bool] = False,
    ):
        self.username = username
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.disabled = disabled


# Mock user database - will be initialized after function definitions
fake_users_db: Dict[str, UserInDB] = {}


def get_user(db: Dict[str, UserInDB], username: str) -> Optional[UserInDB]:
    """Retrieve a user from the mock database."""
    return db.get(username)


# Password Hashing (Production-ready with bcrypt)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed version."""
    # Type safety check
    if not isinstance(hashed_password, str):
        return False

    if BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except (ValueError, TypeError):
            return False
    else:
        # Fallback to SHA256 (not recommended for production)
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    if BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    else:
        # Fallback to SHA256 (not recommended for production)
        return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash a password (alias for get_password_hash for compatibility)."""
    return get_password_hash(password)


# JWT Token Creation (Production-ready with PyJWT)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token using PyJWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    if JWT_AVAILABLE:
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    else:
        # Fallback simulation for testing
        header = '{"alg": "HS256", "typ": "JWT"}'
        payload_str = json.dumps(to_encode, default=str)
        signature_input = f"{header}.{payload_str}.{SECRET_KEY}"
        signature = hashlib.sha256(signature_input.encode()).hexdigest()
        return f"simulated_header.{payload_str}.{signature}"


# JWT Token Decoding (Production-ready with PyJWT)
def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode an access token using PyJWT."""
    try:
        if JWT_AVAILABLE:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        else:
            # Fallback simulation for testing
            parts = token.split(".")
            if len(parts) != 3:
                return None

            try:
                payload = json.loads(parts[1])
            except json.JSONDecodeError:
                return None

            # Check expiration
            if "exp" in payload:
                if isinstance(payload["exp"], str):
                    exp_time = datetime.fromisoformat(payload["exp"].replace("Z", "+00:00"))
                    if exp_time < datetime.now(timezone.utc):
                        return None
                elif isinstance(payload["exp"], (int, float)):
                    if payload["exp"] < time.time():
                        return None

            return payload
    except Exception:
        return None


def generate_api_key() -> str:
    """Generate a secure API key."""
    import secrets

    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str) -> bool:
    """Validate an API key format."""
    return len(api_key) >= 32 and api_key.replace("-", "").replace("_", "").isalnum()


# Initialize the fake database with properly hashed password
fake_users_db["testuser"] = UserInDB(
    username="testuser",
    email="testuser@example.com",
    full_name="Test User",
    hashed_password=get_password_hash("testpassword"),
    disabled=False,
)

# Add test user for auth tests
fake_users_db["authtestuser"] = UserInDB(
    username="authtestuser",
    email="authtestuser@example.com",
    full_name="Auth Test User",
    hashed_password=get_password_hash("authtestpassword"),
    disabled=False,
)
