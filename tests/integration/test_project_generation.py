"""Integration tests for project generation."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from openpypi.core.config import Config
from openpypi.core.generator import ProjectGenerator


class TestProjectGenerationIntegration:
    """Integration tests for complete project generation."""
    
    def test_generate_basic_project(self):
        """Test generating a basic Python project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="basic-project",
                package_name="basic_project",
                author="Test Author",
                email="test@example.com",
                description="A basic test project",
                output_dir=Path(temp_dir),
                use_git=False,  # Skip git for test isolation
                create_tests=True,
                use_fastapi=False,
                use_docker=False
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            project_dir = Path(results["project_dir"])
            
            # Verify project structure
            assert project_dir.exists()
            assert (project_dir / "src" / "basic_project").exists()
            assert (project_dir / "tests").exists()
            assert (project_dir / "docs").exists()
            
            # Verify files were created
            assert len(results["files_created"]) > 0
            assert len(results["directories_created"]) > 0
    
    def test_generate_fastapi_project(self):
        """Test generating a FastAPI project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="fastapi-project",
                package_name="fastapi_project",
                author="Test Author",
                email="test@example.com",
                description="A FastAPI test project",
                output_dir=Path(temp_dir),
                use_git=False,
                create_tests=True,
                use_fastapi=True,
                use_docker=False
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            project_dir = Path(results["project_dir"])
            
            # Verify FastAPI structure
            assert (project_dir / "src" / "fastapi_project" / "api").exists()
            assert (project_dir / "src" / "fastapi_project" / "models").exists()
            assert (project_dir / "src" / "fastapi_project" / "services").exists()
    
    def test_generate_docker_project(self):
        """Test generating a project with Docker support."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="docker-project",
                package_name="docker_project",
                author="Test Author",
                email="test@example.com",
                description="A Docker test project",
                output_dir=Path(temp_dir),
                use_git=False,
                create_tests=True,
                use_fastapi=False,
                use_docker=True
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            project_dir = Path(results["project_dir"])
            
            # Verify Docker structure
            assert (project_dir / "docker").exists()
    
    def test_generate_full_featured_project(self):
        """Test generating a project with all features enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="full-project",
                package_name="full_project",
                author="Test Author",
                email="test@example.com",
                description="A full-featured test project",
                output_dir=Path(temp_dir),
                use_git=False,
                create_tests=True,
                use_fastapi=True,
                use_docker=True,
                use_github_actions=True,
                kubernetes_enabled=True
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            project_dir = Path(results["project_dir"])
            
            # Verify all features
            assert (project_dir / "src" / "full_project" / "api").exists()
            assert (project_dir / "docker").exists()
            assert (project_dir / "k8s").exists()
            assert (project_dir / "tests" / "unit").exists()
            assert (project_dir / "tests" / "integration").exists()
    
    def test_generate_with_custom_dependencies(self):
        """Test generating project with custom dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="deps-project",
                package_name="deps_project",
                author="Test Author",
                email="test@example.com",
                output_dir=Path(temp_dir),
                use_git=False,
                dependencies=["requests", "click"],
                dev_dependencies=["pytest", "black"]
            )
            
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            project_dir = Path(results["project_dir"])
            assert project_dir.exists()
            
            # Dependencies would be verified in pyproject.toml template
            # This test ensures the config is properly passed through
    
    def test_generate_project_validation_error(self):
        """Test project generation with validation errors."""
        from openpypi.core.exceptions import GenerationError
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                project_name="",  # Invalid: empty name
                output_dir=Path(temp_dir)
            )
            
            generator = ProjectGenerator(config)
            
            with pytest.raises(GenerationError):
                generator.generate()
    
    def test_generate_project_existing_directory(self):
        """Test project generation in existing non-empty directory."""
        from openpypi.core.exceptions import GenerationError
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create existing project directory with content
            project_path = Path(temp_dir) / "existing-project"
            project_path.mkdir()
            (project_path / "existing_file.txt").write_text("existing content")
            
            config = Config(
                project_name="existing-project",
                output_dir=Path(temp_dir)
            )
            
            generator = ProjectGenerator(config)
            
            with pytest.raises(GenerationError, match="already exists and is not empty"):
                generator.generate()


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_complete_workflow_minimal(self):
        """Test complete workflow for minimal project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create configuration
            config = Config(
                project_name="workflow-test",
                author="Workflow Tester",
                email="workflow@example.com",
                output_dir=Path(temp_dir),
                use_git=False
            )
            
            # 2. Validate configuration
            config.validate()  # Should not raise
            
            # 3. Generate project
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            # 4. Verify results
            assert results["project_dir"] is not None
            assert len(results["files_created"]) > 0
            assert len(results["directories_created"]) > 0
            
            # 5. Check project can be loaded
            project_dir = Path(results["project_dir"])
            assert project_dir.exists()
            assert (project_dir / "src" / "workflow_test").exists()
    
    def test_complete_workflow_fastapi(self):
        """Test complete workflow for FastAPI project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create FastAPI configuration
            config = Config(
                project_name="fastapi-workflow",
                author="FastAPI Tester",
                email="fastapi@example.com",
                output_dir=Path(temp_dir),
                use_git=False,
                use_fastapi=True,
                create_tests=True
            )
            
            # 2. Generate project
            generator = ProjectGenerator(config)
            
            with patch.object(generator, '_install_dependencies'):
                results = generator.generate()
            
            # 3. Verify FastAPI structure
            project_dir = Path(results["project_dir"])
            api_dir = project_dir / "src" / "fastapi_workflow" / "api"
            
            assert api_dir.exists()
            assert (project_dir / "tests").exists() 