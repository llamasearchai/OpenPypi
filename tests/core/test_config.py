"""
Tests for openpypi.core.config module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from openpypi.core.config import Config, ConfigManager, load_config
from openpypi.core.exceptions import ConfigurationError, ValidationError


class TestConfig:
    """Test the Config class."""

    def test_config_default_initialization(self):
        """Test default config initialization."""
        config = Config()
        assert config.project_name == "example_project"
        assert config.package_name == "example_package"
        assert config.version == "0.1.0"
        assert config.author == "Author Name"
        assert config.email == "author@example.com"
        assert config.use_git is True
        assert config.use_docker is True
        assert config.use_fastapi is True
        assert config.create_tests is True

    def test_config_custom_initialization(self):
        """Test config initialization with custom values."""
        config = Config(
            project_name="my_project",
            package_name="my_package",
            version="1.0.0",
            author="John Doe",
            email="john@example.com",
            use_git=False,
        )
        assert config.project_name == "my_project"
        assert config.package_name == "my_package"
        assert config.version == "1.0.0"
        assert config.author == "John Doe"
        assert config.email == "john@example.com"
        assert config.use_git is False

    def test_config_from_file_toml(self):
        """Test loading config from TOML file."""
        toml_content = """
[openpypi]
project_name = "test_project"
package_name = "test_package"
version = "2.0.0"
author = "Test Author"
email = "test@example.com"
use_git = false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            config = Config.from_file(f.name)
            assert config.project_name == "test_project"
            assert config.package_name == "test_package"
            assert config.version == "2.0.0"
            assert config.use_git is False

    def test_config_from_file_json(self):
        """Test loading config from JSON file."""
        json_data = {
            "project_name": "json_project",
            "package_name": "json_package",
            "version": "3.0.0",
            "author": "JSON Author",
            "email": "json@example.com",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            f.flush()

            config = Config.from_file(f.name)
            assert config.project_name == "json_project"
            assert config.package_name == "json_package"
            assert config.version == "3.0.0"

    def test_config_from_file_not_found(self):
        """Test loading config from non-existent file."""
        with pytest.raises(ConfigurationError):
            Config.from_file("non_existent_file.toml")

    def test_config_from_env(self):
        """Test loading config from environment variables."""
        env_vars = {
            "OPENPYPI_PROJECT_NAME": "env_project",
            "OPENPYPI_PACKAGE_NAME": "env_package",
            "OPENPYPI_VERSION": "4.0.0",
            "OPENPYPI_AUTHOR": "Env Author",
            "OPENPYPI_EMAIL": "env@example.com",
            "OPENPYPI_USE_GIT": "false",
            "OPENPYPI_LINE_LENGTH": "120",
        }

        with patch.dict("os.environ", env_vars):
            config = Config.from_env()
            assert config.project_name == "env_project"
            assert config.package_name == "env_package"
            assert config.version == "4.0.0"
            assert config.use_git is False
            assert config.line_length == 120

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config(project_name="dict_project", package_name="dict_package")

        data = config.to_dict()
        assert isinstance(data, dict)
        assert data["project_name"] == "dict_project"
        assert data["package_name"] == "dict_package"

    def test_config_validation_success(self):
        """Test successful config validation."""
        config = Config(
            project_name="valid_project",
            package_name="valid_package",
            author="Valid Author",
            email="valid@example.com",
        )

        # Should not raise any exception
        config.validate()

    def test_config_validation_missing_required_fields(self):
        """Test config validation with missing required fields."""
        config = Config(
            project_name="",  # Empty project name
            package_name="valid_package",
            author="Valid Author",
            email="valid@example.com",
        )

        with pytest.raises(ValidationError):
            config.validate()

    def test_config_validation_invalid_email(self):
        """Test config validation with invalid email."""
        config = Config(
            project_name="valid_project",
            package_name="valid_package",
            author="Valid Author",
            email="invalid_email",  # Missing @
        )

        with pytest.raises(ValidationError):
            config.validate()

    def test_config_validation_invalid_test_framework(self):
        """Test config validation with invalid test framework."""
        config = Config(
            project_name="valid_project",
            package_name="valid_package",
            author="Valid Author",
            email="valid@example.com",
            test_framework="invalid_framework",
        )

        with pytest.raises(ValidationError):
            config.validate()

    def test_config_update(self):
        """Test updating config values."""
        config = Config()

        config.update(
            project_name="updated_project",
            version="5.0.0",
            unknown_key="should_be_ignored",  # Unknown key
        )

        assert config.project_name == "updated_project"
        assert config.version == "5.0.0"
        # Unknown key should be ignored but not cause error

    def test_config_get(self):
        """Test getting config values."""
        config = Config(project_name="test_project")

        assert config.get("project_name") == "test_project"
        assert config.get("non_existent_key", "default") == "default"
        assert config.get("non_existent_key") is None


class TestConfigManager:
    """Test the ConfigManager class."""

    def test_config_manager_initialization(self):
        """Test config manager initialization."""
        manager = ConfigManager()
        assert manager.config is not None
        assert isinstance(manager.config, Config)

    def test_config_manager_with_custom_config(self):
        """Test config manager with custom config."""
        custom_config = Config(project_name="custom_project")
        manager = ConfigManager(custom_config)
        assert manager.config.project_name == "custom_project"

    def test_config_manager_load_from_file(self):
        """Test loading config from file via manager."""
        toml_content = """
[openpypi]
project_name = "manager_project"
package_name = "manager_package"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            manager = ConfigManager()
            manager.load_from_file(f.name)
            assert manager.config.project_name == "manager_project"

    def test_config_manager_update_config(self):
        """Test updating config via manager."""
        manager = ConfigManager()
        manager.update_config(project_name="updated_manager_project")
        assert manager.config.project_name == "updated_manager_project"

    def test_config_manager_get_set_setting(self):
        """Test getting and setting individual settings."""
        manager = ConfigManager()

        # Test setting
        manager.set_setting("project_name", "setting_project")
        assert manager.config.project_name == "setting_project"

        # Test getting
        value = manager.get_setting("project_name")
        assert value == "setting_project"

        # Test getting with default
        value = manager.get_setting("non_existent", "default_value")
        assert value == "default_value"


class TestLoadConfig:
    """Test the load_config function."""

    def test_load_config_with_file_path(self):
        """Test loading config with provided file path."""
        toml_content = """
[openpypi]
project_name = "load_test_project"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            config = load_config(f.name)
            assert config.project_name == "load_test_project"

    def test_load_config_default_file(self):
        """Test loading config from default file."""
        # Create a default config file
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            toml_content = """
[openpypi]
project_name = "default_file_project"
"""
            with patch("builtins.open", mock_open(read_data=toml_content)):
                with patch("tomllib.load") as mock_load:
                    mock_load.return_value = {"openpypi": {"project_name": "default_file_project"}}

                    config = load_config()
                    assert config.project_name == "default_file_project"

    def test_load_config_fallback_to_default(self):
        """Test loading config falls back to default."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False  # No config files exist

            with patch.dict("os.environ", {}, clear=True):  # No env vars
                config = load_config()
                assert config.project_name == "example_project"  # Default value
