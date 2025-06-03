"""
Secure mock data generation for testing and development.
"""

import os
import secrets
from typing import Dict, List

from faker import Faker
from pydantic import BaseModel, SecretStr

fake = Faker()


class SecureMockUser(BaseModel):
    id: str
    username: str
    email: str
    api_key: SecretStr
    hashed_password: SecretStr


def generate_mock_users(count: int = 5) -> List[SecureMockUser]:
    """Generate secure mock user data."""
    return [
        SecureMockUser(
            id=fake.uuid4(),
            username=fake.user_name(),
            email=fake.email(),
            api_key=SecretStr(secrets.token_urlsafe(32)),
            hashed_password=SecretStr(f"$2b$12${secrets.token_urlsafe(22)}"),
        )
        for _ in range(count)
    ]


def generate_mock_projects(count: int = 3) -> List[Dict]:
    """Generate mock project data."""
    return [
        {
            "id": fake.uuid4(),
            "name": fake.catch_phrase(),
            "description": fake.text(),
            "created_at": fake.date_time_this_year().isoformat(),
            "is_public": fake.boolean(),
            "metadata": {
                "language": fake.random_element(["python", "javascript", "go", "rust"]),
                "framework": fake.random_element(["fastapi", "django", "flask", "none"]),
                "license": fake.random_element(["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"]),
            },
        }
        for _ in range(count)
    ]
