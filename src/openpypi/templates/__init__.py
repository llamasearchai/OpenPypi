"""
Template management system for OpenPypi.
"""

from openpypi.templates.base import Template, TemplateManager

__all__ = ["Template", "TemplateManager"]

"""Template utilities for OpenPypi."""

from pathlib import Path
from typing import Dict, List, Optional


def get_template_path() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent


def get_available_templates() -> List[str]:
    """Get list of available project templates."""
    template_dirs = []
    template_path = get_template_path()

    for item in template_path.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            template_dirs.append(item.name)

    return sorted(template_dirs)


def get_template_info(template_name: str) -> Optional[Dict[str, str]]:
    """Get information about a specific template."""
    template_path = get_template_path() / template_name

    if not template_path.exists():
        return None

    info_file = template_path / "template.json"
    if info_file.exists():
        import json

        with open(info_file) as f:
            return json.load(f)

    return {
        "name": template_name,
        "description": f"Template for {template_name} projects",
        "version": "1.0.0",
    }
