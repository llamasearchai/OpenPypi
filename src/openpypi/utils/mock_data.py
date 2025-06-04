"""
Secure mock data generation for testing and development.
"""

import os
import secrets
from typing import Dict, List, Any
import random
from datetime import datetime, timedelta

from faker import Faker
from pydantic import BaseModel, SecretStr

fake = Faker()


class SecureMockUser(BaseModel):
    id: str
    username: str
    email: str
    api_key: SecretStr
    hashed_password: SecretStr


def generate_mock_users(count: int = 3) -> List[Dict[str, Any]]:
    """Generate mock user data for testing."""
    users = []
    for i in range(count):
        users.append({
            "id": i + 1,
            "username": f"user{i + 1}",
            "email": f"user{i + 1}@example.com",
            "full_name": f"Test User {i + 1}",
            "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
            "is_active": True,
            "role": "user" if i > 0 else "admin"
        })
    return users


def generate_mock_projects(count: int = 5) -> List[Dict[str, Any]]:
    """Generate mock project data for testing."""
    projects = []
    project_types = ["library", "web_api", "cli_tool", "data_science", "ml_toolkit"]
    
    for i in range(count):
        projects.append({
            "id": i + 1,
            "name": f"project{i + 1}",
            "package_name": f"project_{i + 1}",
            "description": f"Test project {i + 1} description",
            "author": f"Author {i + 1}",
            "email": f"author{i + 1}@openpypi.dev",
            "version": f"0.{i + 1}.0",
            "project_type": project_types[i % len(project_types)],
            "use_fastapi": i % 2 == 0,
            "use_docker": i % 3 == 0,
            "use_openai": i % 4 == 0,
            "created_at": datetime.now() - timedelta(days=random.randint(1, 100)),
            "status": "active" if i % 5 != 4 else "archived"
        })
    return projects


def generate_mock_config() -> Dict[str, Any]:
    """Generate mock configuration data."""
    return {
        "project_name": "test-project",
        "package_name": "test_project",
        "author": "Test Author",
        "email": "demo@openpypi.dev",
        "description": "A test project for OpenPypi",
        "version": "0.1.0",
        "license": "MIT",
        "python_requires": ">=3.8",
        "use_fastapi": True,
        "use_docker": True,
        "use_openai": False,
        "create_tests": True,
        "use_git": True,
        "use_github_actions": True,
        "test_framework": "pytest"
    }


def generate_mock_api_response() -> Dict[str, Any]:
    """Generate mock API response data."""
    return {
        "status": "success",
        "message": "Operation completed successfully",
        "data": {
            "project_id": "12345",
            "files_created": 15,
            "directories_created": 8,
            "timestamp": datetime.now().isoformat()
        },
        "metadata": {
            "version": "0.3.0",
            "execution_time": 2.5,
            "warnings": []
        }
    }


def generate_mock_openai_response() -> Dict[str, Any]:
    """Generate mock OpenAI API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mock response from OpenAI API for testing purposes."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150
        }
    }
