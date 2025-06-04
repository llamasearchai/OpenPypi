"""Tests for project generator."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from openpypi.core.config import Config
from openpypi.core.generator import ProjectGenerator
from openpypi.core.exceptions import GenerationError


class TestProjectGenerator:
    """Test ProjectGenerator class."""
    
    def test_generator_creation(self):
        """Test creating ProjectGenerator."""
        config = Config(project_name="test-project")
        generator = ProjectGenerator(config)
        
        assert generator.config == config
        assert generator.template_env is not None
        assert isinstance(generator.results, dict)
    
    def test_generator_with_minimal_config(self):
        """Test generator with minimal configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="minimal-project",
                output_dir=Path(temp_dir)
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_generate_files'), \
                 patch.object(generator, '_initialize_git'), \
                 patch.object(generator, '_install_dependencies'):
                
                results = generator.generate()
                
                assert results["project_dir"] is not None
                assert isinstance(results["files_created"], list)
                assert isinstance(results["directories_created"], list)
                assert isinstance(results["commands_run"], list)
                assert isinstance(results["warnings"], list)
    
    def test_generator_with_fastapi_config(self):
        """Test generator with FastAPI configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="fastapi-project",
                output_dir=Path(temp_dir),
                use_fastapi=True
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_generate_files'), \
                 patch.object(generator, '_initialize_git'), \
                 patch.object(generator, '_install_dependencies'):
                
                results = generator.generate()
                
                assert results["project_dir"] is not None
                project_dir = Path(results["project_dir"])
                assert project_dir.exists()
    
    def test_generator_with_docker_config(self):
        """Test generator with Docker configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="docker-project",
                output_dir=Path(temp_dir),
                use_docker=True
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_generate_files'), \
                 patch.object(generator, '_initialize_git'), \
                 patch.object(generator, '_install_dependencies'):
                
                results = generator.generate()
                
                assert results["project_dir"] is not None
    
    def test_project_directory_creation(self):
        """Test project directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="test-project",
                output_dir=Path(temp_dir)
            )
            
            generator = ProjectGenerator(config)
            project_dir = generator._create_project_directory()
            
            assert project_dir.exists()
            assert project_dir.name == "test-project"
            assert str(project_dir) in generator.results["directories_created"]
    
    def test_project_directory_exists_empty(self):
        """Test handling of existing empty project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test-project"
            project_path.mkdir()
            
            config = Config(
                project_name="test-project",
                output_dir=Path(temp_dir)
            )
            
            generator = ProjectGenerator(config)
            project_dir = generator._create_project_directory()
            
            assert project_dir.exists()
            assert project_dir == project_path
    
    def test_project_directory_exists_not_empty(self):
        """Test handling of existing non-empty project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test-project"
            project_path.mkdir()
            (project_path / "existing_file.txt").write_text("content")
            
            config = Config(
                project_name="test-project",
                output_dir=Path(temp_dir)
            )
            
            generator = ProjectGenerator(config)
            
            with pytest.raises(GenerationError, match="already exists and is not empty"):
                generator._create_project_directory()
    
    def test_generate_project_structure_basic(self):
        """Test generating basic project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test-project"
            project_dir.mkdir()
            
            config = Config(project_name="test-project")
            generator = ProjectGenerator(config)
            
            generator._generate_project_structure(project_dir)
            
            # Check basic directories
            assert (project_dir / "src" / "test_project").exists()
            assert (project_dir / "tests").exists()
            assert (project_dir / "docs").exists()
            assert (project_dir / "scripts").exists()
            assert (project_dir / "configs").exists()
    
    def test_generate_project_structure_with_fastapi(self):
        """Test generating project structure with FastAPI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test-project"
            project_dir.mkdir()
            
            config = Config(
                project_name="test-project",
                use_fastapi=True
            )
            generator = ProjectGenerator(config)
            
            generator._generate_project_structure(project_dir)
            
            # Check FastAPI directories
            assert (project_dir / "src" / "test_project" / "api").exists()
            assert (project_dir / "src" / "test_project" / "models").exists()
            assert (project_dir / "src" / "test_project" / "services").exists()
    
    def test_generate_project_structure_with_docker(self):
        """Test generating project structure with Docker."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test-project"
            project_dir.mkdir()
            
            config = Config(
                project_name="test-project",
                use_docker=True
            )
            generator = ProjectGenerator(config)
            
            generator._generate_project_structure(project_dir)
            
            # Check Docker directory
            assert (project_dir / "docker").exists()
    
    def test_get_template_context(self):
        """Test getting template context."""
        config = Config(
            project_name="test-project",
            author="John Doe",
            email="john@example.com",
            use_fastapi=True,
            use_docker=True
        )
        
        generator = ProjectGenerator(config)
        context = generator._get_template_context()
        
        assert context["project_name"] == "test-project"
        assert context["package_name"] == "test_project"
        assert context["author"] == "John Doe"
        assert context["email"] == "john@example.com"
        assert context["use_fastapi"] is True
        assert context["use_docker"] is True
        assert "config" in context
    
    @patch('subprocess.run')
    def test_initialize_git_success(self, mock_run):
        """Test successful git initialization."""
        mock_run.return_value.returncode = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config = Config(project_name="test-project")
            generator = ProjectGenerator(config)
            
            generator._initialize_git(project_dir)
            
            assert "git init" in generator.results["commands_run"]
            assert "git commit -m 'Initial commit'" in generator.results["commands_run"]
    
    @patch('subprocess.run')
    def test_initialize_git_failure(self, mock_run):
        """Test git initialization failure."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "git")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config = Config(project_name="test-project")
            generator = ProjectGenerator(config)
            
            generator._initialize_git(project_dir)
            
            assert len(generator.results["warnings"]) > 0
            assert "Git initialization failed" in generator.results["warnings"][0]
    
    @patch('subprocess.run')
    def test_install_dependencies_success(self, mock_run):
        """Test successful dependency installation."""
        mock_run.return_value.returncode = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config = Config(
                project_name="test-project",
                dependencies=["fastapi", "uvicorn"]
            )
            generator = ProjectGenerator(config)
            
            generator._install_dependencies(project_dir)
            
            assert "python -m venv venv" in generator.results["commands_run"]
            assert "pip install -e .[dev]" in generator.results["commands_run"]
    
    def test_install_dependencies_no_deps(self):
        """Test dependency installation with no dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config = Config(project_name="test-project")
            generator = ProjectGenerator(config)
            
            generator._install_dependencies(project_dir)
            
            # Should not run any commands when no dependencies
            assert len(generator.results["commands_run"]) == 0


class TestProjectGeneratorIntegration:
    """Integration tests for ProjectGenerator."""
    
    def test_generate_minimal_project(self):
        """Test generating a minimal project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="minimal-test",
                output_dir=Path(temp_dir),
                use_git=False,  # Skip git to avoid external dependencies
                create_tests=False  # Simplify for test
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            project_dir = Path(results["project_dir"])
            
            # Verify project directory was created
            assert project_dir.exists()
            assert project_dir.name == "minimal-test"
            
            # Verify basic structure
            assert (project_dir / "src" / "minimal_test").exists()
            assert len(results["directories_created"]) > 0 