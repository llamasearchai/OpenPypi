"""Tests for configuration management."""

import json
import tempfile
from pathlib import Path

import pytest
import toml

from openpypi.core.config import Config, ConfigManager, load_config
from openpypi.core.exceptions import ConfigurationError, ValidationError


class TestConfig:
    """Test Config class."""
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = Config(project_name="test-project")
        
        assert config.project_name == "test-project"
        assert config.package_name == "test_project"
        assert config.author == "Developer"
        assert config.email == "developer@example.com"
        assert config.version == "0.1.0"
        assert config.license == "MIT"
        assert config.python_requires == ">=3.8"
        assert config.use_fastapi is False
        assert config.use_openai is False
        assert config.use_docker is False
        assert config.create_tests is True
        assert config.test_framework == "pytest"
    
    def test_config_creation_with_custom_values(self):
        """Test creating config with custom values."""
        config = Config(
            project_name="my-awesome-project",
            package_name="my_awesome_package",
            author="John Doe",
            email="john@example.com",
            description="An awesome project",
            version="1.0.0",
            use_fastapi=True,
            use_docker=True,
            use_openai=True
        )
        
        assert config.project_name == "my-awesome-project"
        assert config.package_name == "my_awesome_package"
        assert config.author == "John Doe"
        assert config.email == "john@example.com"
        assert config.description == "An awesome project"
        assert config.version == "1.0.0"
        assert config.use_fastapi is True
        assert config.use_docker is True
        assert config.use_openai is True
    
    def test_package_name_auto_generation(self):
        """Test automatic package name generation from project name."""
        config = Config(project_name="my-test-project")
        assert config.package_name == "my_test_project"
        
        config = Config(project_name="MyTestProject")
        assert config.package_name == "mytestproject"
    
    def test_description_auto_generation(self):
        """Test automatic description generation."""
        config = Config(project_name="test-project")
        assert config.description == "A Python package for test-project"
    
    def test_config_validation_success(self):
        """Test successful config validation."""
        config = Config(
            project_name="valid-project",
            author="John Doe",
            email="john@example.com"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_config_validation_failures(self):
        """Test config validation failures."""
        # Empty project name
        with pytest.raises(ValidationError, match="Project name is required"):
            config = Config(project_name="")
            config.validate()
        
        # Invalid email
        with pytest.raises(ValidationError, match="Invalid email format"):
            config = Config(project_name="test", email="invalid-email")
            config.validate()
        
        # Invalid version format
        with pytest.raises(ValidationError, match="Version must be in format"):
            config = Config(project_name="test", version="invalid")
            config.validate()
        
        # Invalid test framework
        with pytest.raises(ValidationError, match="Test framework must be"):
            config = Config(project_name="test", test_framework="invalid")
            config.validate()
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config(
            project_name="test-project",
            author="John Doe",
            use_fastapi=True
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["project_name"] == "test-project"
        assert config_dict["author"] == "John Doe"
        assert config_dict["use_fastapi"] is True


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_config_manager_creation(self):
        """Test creating ConfigManager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            manager = ConfigManager(config_dir)
            
            assert manager.config_dir == config_dir
    
    def test_config_manager_default_dir(self):
        """Test ConfigManager with default directory."""
        manager = ConfigManager()
        assert manager.config_dir == Path.cwd()
    
    def test_save_and_load_config(self):
        """Test saving and loading config through manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            manager = ConfigManager(config_dir)
            
            # Create and save config
            config = Config(
                project_name="test-project",
                author="John Doe",
                use_fastapi=True
            )
            
            manager.save_config(config, "test")
            
            # Load config
            loaded_config = manager.load_config("test")
            
            assert loaded_config.project_name == "test-project"
            assert loaded_config.author == "John Doe"
            assert loaded_config.use_fastapi is True
    
    def test_list_configs(self):
        """Test listing available configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            manager = ConfigManager(config_dir)
            
            # Create some config files
            config1 = Config(project_name="project1")
            config2 = Config(project_name="project2")
            
            manager.save_config(config1, "config1")
            manager.save_config(config2, "config2")
            
            configs = manager.list_configs()
            assert "config1" in configs
            assert "config2" in configs


class TestLoadConfig:
    """Test load_config function."""
    
    def test_load_config_from_file(self):
        """Test loading config from specific file."""
        config_data = {
            "project_name": "test-project",
            "author": "John Doe",
            "use_fastapi": True
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            config_file = Path(f.name)
            toml.dump(config_data, f)
        
        try:
            config = load_config(config_file)
            
            assert config.project_name == "test-project"
            assert config.author == "John Doe"
            assert config.use_fastapi is True
        finally:
            config_file.unlink(missing_ok=True)
    
    def test_load_config_from_env(self):
        """Test loading config from environment when no file specified."""
        config = load_config()
        
        # Should return a valid config with defaults
        assert isinstance(config, Config)
        assert config.author == "Developer"
        assert config.email == "developer@example.com" 