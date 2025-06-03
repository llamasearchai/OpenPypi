"""
API routes for user authentication and authorization.
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from openpypi.api.dependencies import get_api_key, get_config, get_current_user
from openpypi.api.schemas import APIResponse, Token, User, UserCreate
from openpypi.core.config import Config

# In a real application, you would use a proper security utility library
# For example, passlib for password hashing, and python-jose for JWTs.
# This is a simplified placeholder.
from openpypi.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    UserInDB,
    create_access_token,
    fake_users_db,
    get_password_hash,
)
from openpypi.core.security import get_user as get_db_user  # A mock user database for demonstration
from openpypi.core.security import (
    verify_password,
)
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_user_database(config: Config) -> dict:
    """Get the user database, checking config override first."""
    if config.fake_users_db_override:
        return config.fake_users_db_override
    return fake_users_db


def authenticate_user(db: dict, username: str, password: str) -> UserInDB | None:
    """Authenticate a user. Placeholder implementation."""
    user = get_db_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


@router.post(
    "/token",
    response_model=Token,
    summary="Get Access Token",
    description="Authenticates a user and returns an access token.",
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), config: Config = Depends(get_config)
):
    """Provides an access token for valid credentials."""
    # Use the config's user database override if available
    user_db = get_user_database(config)
    user = authenticate_user(user_db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Authentication failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=getattr(config, "access_token_expire_minutes", ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.info(f"Access token generated for user: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Registers a new user in the system.",
)
async def register_user(user_data: UserCreate, config: Config = Depends(get_config)):
    """Registers a new user."""
    username = user_data.username

    # Use the config's user database override if available
    user_db = get_user_database(config)

    if username in user_db:
        logger.warning(f"Attempt to register existing user: {username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    # In a real app, save the user to the database here.
    user_db[username] = UserInDB(
        username=username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
    )
    logger.info(f"User registered: {username}")

    # Return the created user (excluding password)
    return User(
        username=username, email=user_data.email, full_name=user_data.full_name, disabled=False
    )


@router.get(
    "/users/me",
    response_model=User,
    summary="Get Current User Information",
    description="Returns information about the currently authenticated user.",
)
async def read_users_me(
    current_user: dict = Depends(get_current_user), config: Config = Depends(get_config)
):
    """Returns the current authenticated user's details."""
    # get_current_user returns a dict with user info from API key validation
    username = current_user.get("username", "authenticated_user")

    # Use the config's user database override if available
    user_db = get_user_database(config)

    # Try to get user from database
    user_from_db = get_db_user(user_db, username)
    if user_from_db:
        return User(
            username=user_from_db.username,
            email=user_from_db.email,
            full_name=user_from_db.full_name,
            disabled=user_from_db.disabled,
        )

    # Fallback for API key users not in fake_db
    return User(
        username=username,
        email=current_user.get("email", "api@example.com"),
        full_name=current_user.get("full_name", "API User"),
        disabled=False,
    )


@router.get(
    "/validate-key",
    response_model=APIResponse,
    summary="Validate API Key",
    description="Validates the provided API key (X-API-Key header).",
)
async def validate_api_key(api_key: str = Depends(get_api_key)):
    """Endpoint to explicitly validate an API key."""
    # If we get here, the API key is valid (get_api_key dependency passed)
    logger.info(f"API key validated successfully")
    return APIResponse(
        success=True,
        message="API key is valid.",
        data={"api_key": api_key[:8] + "...", "status": "valid"},
    )


@router.get(
    "/validate-token",
    response_model=APIResponse,
    summary="Validate API Token",
    description="Validates the provided API token (X-API-Key header).",
)
async def validate_token(current_user: dict = Depends(get_current_user)):
    """Endpoint to explicitly validate an API token."""
    logger.info(f"Token validated successfully for user: {current_user.get('username')}")
    return APIResponse(success=True, message="Token is valid.", data=current_user)
