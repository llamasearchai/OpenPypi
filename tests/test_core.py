"""Tests for core functionality."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from openpypi.core import Config, ProjectGenerator
from openpypi.core.exceptions import ValidationError, ConfigurationError, GenerationError


class TestConfig:
    """Test cases for Config class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        assert config.project_name == "example_project"
        assert config.package_name == "example_package"
        assert config.author == "Author Name"
        assert config.use_fastapi is True
        assert config.use_openai is True
    
    def test_config_validation_success(self, sample_config):
        """Test successful configuration validation."""
        sample_config.validate()  # Should not raise
    
    def test_config_validation_missing_required(self):
        """Test validation with missing required fields."""
        config = Config(project_name="", author="", email="")
        
        with pytest.raises(ValidationError) as exc_info:
            config.validate()
        
        assert "project_name is required" in str(exc_info.value)
        assert "author is required" in str(exc_info.value)
        assert "email is required" in str(exc_info.value)
    
    def test_config_validation_invalid_email(self):
        """Test validation with invalid email."""
        config = Config(email="invalid-email")
        
        with pytest.raises(ValidationError) as exc_info:
            config.validate()
        
        assert "email must be a valid email address" in str(exc_info.value)
    
    def test_config_validation_invalid_test_framework(self):
        """Test validation with invalid test framework."""
        config = Config(test_framework="invalid")
        
        with pytest.raises(ValidationError) as exc_info:
            config.validate()
        
        assert "test_framework must be 'pytest' or 'unittest'" in str(exc_info.value)
    
    def test_config_to_dict(self, sample_config):
        """Test configuration to dictionary conversion."""
        config_dict = sample_config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["project_name"] == "test_project"
        assert config_dict["package_name"] == "test_package"
        assert config_dict["author"] == "Test Author"
    
    def test_config_update(self, sample_config):
        """Test configuration update."""
        original_author = sample_config.author
        sample_config.update(author="New Author", version="2.0.0")
        
        assert sample_config.author == "New Author"
        assert sample_config.version == "2.0.0"
        assert sample_config.author != original_author
    
    def test_config_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("OPENPYPI_PROJECT_NAME", "env_project")
        monkeypatch.setenv("OPENPYPI_AUTHOR", "Env Author")
        monkeypatch.setenv("OPENPYPI_USE_FASTAPI", "false")
        
        config = Config.from_env()
        
        assert config.project_name == "env_project"
        assert config.author == "Env Author"
        assert config.use_fastapi is False
    
    def test_config_from_file_json(self, tmp_path):
        """Test loading configuration from JSON file."""
        config_data = {
            "project_name": "json_project",
            "author": "JSON Author",
            "use_docker": False
        }
        
        config_file = tmp_path / "config.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = Config.from_file(config_file)
        
        assert config.project_name == "json_project"
        assert config.author == "JSON Author"
        assert config.use_docker is False
    
    def test_config_from_file_not_found(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(ConfigurationError) as exc_info:
            Config.from_file("non_existent.toml")
        
        assert "Configuration file not found" in str(exc_info.value)


class TestProjectGenerator:
    """Test cases for ProjectGenerator class."""
    
    def test_generator_initialization(self, sample_config):
        """Test project generator initialization."""
        generator = ProjectGenerator(sample_config)
        
        assert generator.config == sample_config
        assert generator.base_generator is not None
        assert generator.config_formatter is not None
    
    def test_get_dependencies_fastapi(self, sample_config):
        """Test dependency list with FastAPI enabled."""
        generator = ProjectGenerator(sample_config)
        deps = generator._get_dependencies()
        
        assert 'fastapi>=0.104.0' in deps
        assert 'uvicorn>=0.24.0' in deps
    
    def test_get_dependencies_openai(self, sample_config):
        """Test dependency list with OpenAI enabled."""
        generator = ProjectGenerator(sample_config)
        deps = generator._get_dependencies()
        
        assert 'openai>=1.0.0' in deps
    
    def test_get_dependencies_minimal(self, minimal_config):
        """Test dependency list with minimal configuration."""
        generator = ProjectGenerator(minimal_config)
        deps = generator._get_dependencies()
        
        # Should not include FastAPI or OpenAI
        fastapi_deps = [dep for dep in deps if 'fastapi' in dep]
        openai_deps = [dep for dep in deps if 'openai' in dep]
        
        assert len(fastapi_deps) == 0
        assert len(openai_deps) == 0
    
    def test_merge_results(self, project_generator):
        """Test merging results from sub-operations."""
        target = {
            'files_created': ['file1.py'],
            'directories_created': ['dir1'],
            'commands_run': ['cmd1'],
            'warnings': ['warning1']
        }
        
        source = {
            'files_created': ['file2.py'],
            'directories_created': ['dir2'],
            'commands_run': ['cmd2'],
            'warnings': ['warning2']
        }
        
        project_generator._merge_results(target, source)
        
        assert target['files_created'] == ['file1.py', 'file2.py']
        assert target['directories_created'] == ['dir1', 'dir2']
        assert target['commands_run'] == ['cmd1', 'cmd2']
        assert target['warnings'] == ['warning1', 'warning2']
    
    @patch('subprocess.run')
    def test_initialize_git_success(self, mock_run, project_generator, tmp_path):
        """Test successful git initialization."""
        mock_run.return_value = Mock(returncode=0)
        
        results = project_generator._initialize_git(tmp_path)
        
        assert 'git init' in results['commands_run']
        assert 'git add .' in results['commands_run']
        assert 'git commit -m "Initial commit"' in results['commands_run']
        assert len(results['warnings']) == 0
    
    @patch('subprocess.run')
    def test_initialize_git_failure(self, mock_run, project_generator, tmp_path):
        """Test git initialization failure."""
        mock_run.side_effect = FileNotFoundError("git not found")
        
        results = project_generator._initialize_git(tmp_path)
        
        assert len(results['commands_run']) == 0
        assert any('Git not found' in warning for warning in results['warnings'])
    
    def test_generate_main_module(self, project_generator):
        """Test main module generation."""
        content = project_generator._generate_main_module()
        
        assert 'class TestPackage:' in content
        assert 'def run(self)' in content
        assert 'def process_data(self, data:' in content
        assert 'if __name__ == "__main__":' in content
    
    def test_generate_cli_module(self, project_generator):
        """Test CLI module generation."""
        content = project_generator._generate_cli_module()
        
        assert 'def create_parser()' in content
        assert 'def main(' in content
        assert 'argparse.ArgumentParser' in content
        assert 'test_package' in content
    
    def test_generate_fastapi_app(self, project_generator):
        """Test FastAPI app generation."""
        content = project_generator._generate_fastapi_app()
        
        assert 'from fastapi import FastAPI' in content
        assert 'app = FastAPI(' in content
        assert '@app.get("/")' in content
        assert '@app.get("/health")' in content
    
    def test_generate_dockerfile(self, project_generator):
        """Test Dockerfile generation."""
        content = project_generator._generate_dockerfile()
        
        assert 'FROM python:3.11-slim' in content
        assert 'WORKDIR /app' in content
        assert 'COPY requirements.txt .' in content
        assert 'EXPOSE 8000' in content  # FastAPI enabled
        assert 'uvicorn' in content
    
    def test_generate_docker_compose_fastapi(self, project_generator):
        """Test docker-compose generation with FastAPI."""
        content = project_generator._generate_docker_compose()
        
        assert 'version: \'3.8\'' in content
        assert 'ports:' in content
        assert '"8000:8000"' in content
    
    def test_generate_docker_compose_minimal(self, minimal_config):
        """Test docker-compose generation without FastAPI."""
        generator = ProjectGenerator(minimal_config)
        content = generator._generate_docker_compose()
        
        assert 'version: \'3.8\'' in content
        assert 'ports:' not in content  # No FastAPI
    
    def test_generate_readme(self, project_generator):
        """Test README generation."""
        content = project_generator._generate_readme()
        
        assert '# test_project' in content
        assert 'A test package' in content
        assert 'FastAPI web framework' in content
        assert 'OpenAI integration' in content
        assert 'Docker support' in content
    
    def test_generate_github_workflow(self, project_generator):
        """Test GitHub Actions workflow generation."""
        content = project_generator._generate_github_workflow()
        
        assert 'name: CI' in content
        assert 'on:' in content
        assert 'pytest --cov=test_package' in content
        assert 'matrix:' in content
        assert 'python-version:' in content
    
    @patch('subprocess.run')
    def test_create_project_structure(self, mock_run, project_generator, tmp_path):
        """Test project structure creation."""
        project_generator.config.output_dir = tmp_path
        
        results = project_generator._create_project_structure(tmp_path)
        
        # Check that directories were created
        assert 'src/test_package' in results['directories_created']
        assert 'tests' in results['directories_created']
        assert 'docs' in results['directories_created']
        
        # FastAPI-specific directories
        assert 'src/test_package/api' in results['directories_created']
        assert 'src/test_package/models' in results['directories_created']
        assert 'src/test_package/services' in results['directories_created']
        
        # Check that __init__.py files were created
        init_files = [f for f in results['files_created'] if '__init__.py' in f]
        assert len(init_files) > 0
    
    def test_create_requirements_files(self, project_generator, tmp_path):
        """Test requirements files creation."""
        results = {'files_created': [], 'directories_created': [], 'warnings': []}
        
        project_generator._create_requirements_files(tmp_path, results)
        
        assert 'requirements.txt' in results['files_created']
        assert 'requirements-dev.txt' in results['files_created']
        
        # Check file contents
        requirements_file = tmp_path / 'requirements.txt'
        assert requirements_file.exists()
        
        dev_requirements_file = tmp_path / 'requirements-dev.txt'
        assert dev_requirements_file.exists()
        
        dev_content = dev_requirements_file.read_text()
        assert '-r requirements.txt' in dev_content
        assert 'pytest>=7.0.0' in dev_content


class TestProjectGeneratorIntegration:
    """Integration tests for full project generation."""
    
    @patch('subprocess.run')
    def test_full_project_generation(self, mock_run, sample_config, tmp_path):
        """Test complete project generation workflow."""
        # Mock subprocess calls to avoid actual git/pip operations
        mock_run.return_value = Mock(returncode=0)
        
        sample_config.output_dir = tmp_path
        sample_config.use_git = False  # Skip git for testing
        
        generator = ProjectGenerator(sample_config)
        results = generator.generate()
        
        # Check basic structure
        project_dir = Path(results['project_dir'])
        assert project_dir.exists()
        assert (project_dir / 'src' / 'test_package').exists()
        assert (project_dir / 'tests').exists()
        
        # Check configuration files
        assert (project_dir / 'pyproject.toml').exists()
        assert (project_dir / 'requirements.txt').exists()
        assert (project_dir / '.gitignore').exists()
        
        # Check source files
        assert (project_dir / 'src' / 'test_package' / 'main.py').exists()
        assert (project_dir / 'src' / 'test_package' / 'cli.py').exists()
        assert (project_dir / 'src' / 'test_package' / 'utils.py').exists()
        
        # Check FastAPI files
        assert (project_dir / 'src' / 'test_package' / 'api' / 'app.py').exists()
        assert (project_dir / 'src' / 'test_package' / 'api' / 'routes.py').exists()
        assert (project_dir / 'src' / 'test_package' / 'models' / 'schemas.py').exists()
        
        # Check OpenAI integration
        assert (project_dir / 'src' / 'test_package' / 'services' / 'openai_client.py').exists()
        
        # Check Docker files
        assert (project_dir / 'Dockerfile').exists()
        assert (project_dir / 'docker-compose.yml').exists()
        assert (project_dir / '.dockerignore').exists()
        
        # Check documentation
        assert (project_dir / 'README.md').exists()
        assert (project_dir / 'CHANGELOG.md').exists()
        assert (project_dir / 'LICENSE').exists()
        
        # Check CI/CD
        assert (project_dir / '.github' / 'workflows' / 'ci.yml').exists()
        
        # Check results
        assert len(results['files_created']) > 0
        assert len(results['directories_created']) > 0
        assert 'warnings' in results
    
    @patch('subprocess.run')
    def test_minimal_project_generation(self, mock_run, minimal_config, tmp_path):
        """Test minimal project generation without optional features."""
        mock_run.return_value = Mock(returncode=0)
        
        minimal_config.output_dir = tmp_path
        minimal_config.use_git = False
        minimal_config.use_github_actions = False
        
        generator = ProjectGenerator(minimal_config)
        results = generator.generate()
        
        project_dir = Path(results['project_dir'])
        
        # Should not have FastAPI files
        assert not (project_dir / 'src' / 'minimal_package' / 'api').exists()
        
        # Should not have OpenAI files
        assert not (project_dir / 'src' / 'minimal_package' / 'services' / 'openai_client.py').exists()
        
        # Should not have Docker files
        assert not (project_dir / 'Dockerfile').exists()
        
        # Should not have CI/CD files
        assert not (project_dir / '.github').exists()
        
        # Should still have basic structure
        assert (project_dir / 'src' / 'minimal_package' / 'main.py').exists()
        assert (project_dir / 'pyproject.toml').exists()


@pytest.mark.parametrize("invalid_config", [
    {"project_name": ""},
    {"author": ""},
    {"email": "invalid-email"},
    {"test_framework": "invalid"},
    {"line_length": 25},  # Too small
])
def test_config_validation_parametrized(invalid_config):
    """Test configuration validation with various invalid inputs."""
    config = Config(**invalid_config)
    
    with pytest.raises(ValidationError):
        config.validate() 