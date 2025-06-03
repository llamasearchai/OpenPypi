"""
Secure PyPI package publishing functionality.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from twine.commands.upload import upload as twine_upload
from twine.settings import Settings

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PyPIPublisher:
    def __init__(self):
        load_dotenv()
        self.settings = Settings(
            username="__token__",
            password=os.getenv("PYPI_API_TOKEN"),  # From .env
            repository_url=os.getenv("PYPI_REPOSITORY_URL", "https://upload.pypi.org/legacy/"),
        )

    def publish(self, dist_dir: Optional[Path] = None) -> bool:
        """Securely publish package to PyPI."""
        try:
            dist_dir = dist_dir or Path("dist")
            if not dist_dir.exists():
                raise FileNotFoundError(f"Distribution directory {dist_dir} not found")

            logger.info(f"Publishing packages from {dist_dir}")
            twine_upload(self.settings, [str(p) for p in dist_dir.glob("*")])
            return True
        except Exception as e:
            logger.error(f"Publication failed: {e}")
            return False
