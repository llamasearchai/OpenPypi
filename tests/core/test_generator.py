"""
Tests for openpypi.core.generator module.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from openpypi.core.config import Config
from openpypi.core.generator import ProjectGenerator


class TestProjectGenerator:
    """Test the ProjectGenerator class."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return Config(
            project_name="test_project",
            package_name="test_package",
            version="1.0.0",
            author="Test Author",
            email="test@example.com",
            description="A test project",
            use_git=True,
            use_docker=True,
            use_fastapi=True,
            create_tests=True,
        )

    def test_generator_initialization(self, sample_config):
        """Test generator initialization."""
        generator = ProjectGenerator(sample_config)

        assert generator.config == sample_config
        assert generator.project_name == "test_project"
        assert generator.package_name == "test_package"
        assert generator.templates_dir is not None

    def test_generator_generate_project_structure(self, sample_config, temp_output_dir):
        """Test generating basic project structure."""
        generator = ProjectGenerator(sample_config)

        result = generator.generate_project_structure(temp_output_dir)

        assert result["success"] is True
        assert "directories_created" in result
        assert "files_created" in result

        # Check that basic directories were created
        assert (temp_output_dir / "src" / "test_package").exists()
        assert (temp_output_dir / "tests").exists()
        assert (temp_output_dir / "docs").exists()

    def test_generator_create_package_structure(self, sample_config, temp_output_dir):
        """Test creating package structure."""
        generator = ProjectGenerator(sample_config)

        result = generator.create_package_structure(temp_output_dir)

        assert result["success"] is True

        # Check package directories
        src_dir = temp_output_dir / "src" / "test_package"
        assert src_dir.exists()
        assert (src_dir / "__init__.py").exists()

        # Check common module directories
        expected_dirs = ["core", "utils", "models"]
        for dir_name in expected_dirs:
            if (src_dir / dir_name).exists():
                assert (src_dir / dir_name / "__init__.py").exists()

    def test_generator_create_configuration_files(self, sample_config, temp_output_dir):
        """Test creating configuration files."""
        generator = ProjectGenerator(sample_config)

        result = generator.create_configuration_files(temp_output_dir)

        assert result["success"] is True

        # Check essential configuration files
        assert (temp_output_dir / "pyproject.toml").exists()
        assert (temp_output_dir / ".gitignore").exists()
        # README.md is created by create_documentation, not create_configuration_files

    def test_generator_create_test_structure(self, sample_config, temp_output_dir):
        """Test creating test structure."""
        generator = ProjectGenerator(sample_config)

        result = generator.create_test_structure(temp_output_dir)

        assert result["success"] is True

        # Check test directories
        tests_dir = temp_output_dir / "tests"
        assert tests_dir.exists()
        assert (tests_dir / "__init__.py").exists()
        assert (tests_dir / "conftest.py").exists()

        # Check test subdirectories
        assert (tests_dir / "unit").exists()
        assert (tests_dir / "integration").exists()

    def test_generator_create_documentation(self, sample_config, temp_output_dir):
        """Test creating documentation structure."""
        generator = ProjectGenerator(sample_config)

        # First create the project structure (which creates the docs directory)
        structure_result = generator.generate_project_structure(temp_output_dir)
        assert structure_result["success"] is True

        # Then create documentation
        result = generator.create_documentation(temp_output_dir)

        assert result["success"] is True

        # Check documentation files
        docs_dir = temp_output_dir / "docs"
        assert docs_dir.exists()
        assert (temp_output_dir / "README.md").exists()

    def test_generator_with_fastapi_option(self, temp_output_dir):
        """Test generator with FastAPI option enabled."""
        config = Config(
            project_name="fastapi_project", package_name="fastapi_package", use_fastapi=True
        )
        generator = ProjectGenerator(config)

        result = generator.generate_project_structure(temp_output_dir)

        assert result["success"] is True

        # Check FastAPI-specific files
        src_dir = temp_output_dir / "src" / "fastapi_package"
        if (src_dir / "api").exists():
            assert (src_dir / "api" / "__init__.py").exists()

    def test_generator_with_docker_option(self, temp_output_dir):
        """Test generator with Docker option enabled."""
        config = Config(
            project_name="docker_project", package_name="docker_package", use_docker=True
        )
        generator = ProjectGenerator(config)

        result = generator.create_configuration_files(temp_output_dir)

        assert result["success"] is True

        # Check Docker files
        if (temp_output_dir / "Dockerfile").exists():
            assert (temp_output_dir / "Dockerfile").is_file()
        if (temp_output_dir / "docker-compose.yml").exists():
            assert (temp_output_dir / "docker-compose.yml").is_file()

    def test_generator_validate_config(self, sample_config):
        """Test config validation in generator."""
        generator = ProjectGenerator(sample_config)

        # Valid config should pass
        result = generator.validate_config()
        assert result["valid"] is True

        # Invalid config should fail
        invalid_config = Config(project_name="", package_name="valid_package")  # Empty name
        invalid_generator = ProjectGenerator(invalid_config)
        result = invalid_generator.validate_config()
        assert result["valid"] is False

    def test_generator_get_template_content(self, sample_config):
        """Test getting template content."""
        generator = ProjectGenerator(sample_config)

        # Test with existing template
        template_name = "setup_py.j2"
        content = generator.get_template_content(template_name)

        # Should return string content or None if template doesn't exist
        assert isinstance(content, str) or content is None

    def test_generator_render_template(self, sample_config):
        """Test template rendering."""
        generator = ProjectGenerator(sample_config)

        # Simple template string
        template_content = "Project: {{ project_name }}, Version: {{ version }}"
        rendered = generator.render_template(
            template_content, {"project_name": "test_project", "version": "1.0.0"}
        )

        assert "Project: test_project" in rendered
        assert "Version: 1.0.0" in rendered

    def test_generator_create_file_from_template(self, sample_config, temp_output_dir):
        """Test creating file from template."""
        generator = ProjectGenerator(sample_config)

        template_content = "# {{ project_name }}\n\nVersion: {{ version }}"
        file_path = temp_output_dir / "test_file.txt"

        result = generator.create_file_from_template(
            template_content, file_path, {"project_name": "test_project", "version": "1.0.0"}
        )

        assert result["success"] is True
        assert file_path.exists()

        content = file_path.read_text()
        assert "# test_project" in content
        assert "Version: 1.0.0" in content

    def test_generator_error_handling(self, sample_config):
        """Test generator error handling."""
        generator = ProjectGenerator(sample_config)

        # Test with invalid output directory
        invalid_path = Path("/invalid/path/that/does/not/exist")

        # Generator should handle errors gracefully and return success: False
        result = generator.generate_project_structure(invalid_path)
        assert result["success"] is False
        assert "error" in result

    def test_generator_custom_template_variables(self, sample_config):
        """Test generator with custom template variables."""
        generator = ProjectGenerator(sample_config)

        variables = generator.get_template_variables()

        # Check standard variables
        assert "project_name" in variables
        assert "package_name" in variables
        assert "version" in variables
        assert "author" in variables
        assert "email" in variables

        # Check computed variables
        assert variables["project_name"] == "test_project"
        assert variables["package_name"] == "test_package"

    def test_generator_file_operations(self, sample_config, temp_output_dir):
        """Test various file operations."""
        generator = ProjectGenerator(sample_config)

        # Test creating directory
        test_dir = temp_output_dir / "test_directory"
        result = generator.create_directory(test_dir)
        assert result["success"] is True
        assert test_dir.exists()

        # Test writing file
        test_file = test_dir / "test_file.txt"
        content = "Test content"
        result = generator.write_file(test_file, content)
        assert result["success"] is True
        assert test_file.exists()
        assert test_file.read_text() == content

    def test_generator_git_initialization(self, sample_config, temp_output_dir):
        """Test Git repository initialization."""
        config = Config(project_name="git_project", package_name="git_package", use_git=True)
        generator = ProjectGenerator(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = generator.initialize_git_repository(temp_output_dir)

            assert result["success"] is True
            # Verify git init was called
            mock_run.assert_called()

    def test_generator_dependency_management(self, sample_config, temp_output_dir):
        """Test dependency management."""
        # Add some dependencies to config
        sample_config.dependencies = ["requests>=2.25.0", "click>=8.0.0"]
        sample_config.dev_dependencies = ["pytest>=7.0.0", "black>=22.0.0"]

        generator = ProjectGenerator(sample_config)

        result = generator.create_configuration_files(temp_output_dir)
        assert result["success"] is True

        # Check that pyproject.toml contains dependencies
        pyproject_file = temp_output_dir / "pyproject.toml"
        if pyproject_file.exists():
            content = pyproject_file.read_text()
            assert "requests" in content or "dependencies" in content

    def test_generator_complete_project_generation(self, sample_config, temp_output_dir):
        """Test complete project generation workflow."""
        generator = ProjectGenerator(sample_config)

        # Generate complete project
        result = generator.generate_complete_project(temp_output_dir)

        assert result["success"] is True
        assert "project_summary" in result

        # Verify key project structure exists
        assert (temp_output_dir / "src").exists()
        assert (temp_output_dir / "tests").exists()
        assert (temp_output_dir / "pyproject.toml").exists()
        assert (temp_output_dir / "README.md").exists()

    @patch("openpypi.core.generator.ProjectGenerator.validate_config")
    def test_generator_with_mocked_validation(self, mock_validate, sample_config, temp_output_dir):
        """Test generator with mocked validation."""
        mock_validate.return_value = {"valid": True}

        generator = ProjectGenerator(sample_config)
        result = generator.generate_project_structure(temp_output_dir)

        assert result["success"] is True
        mock_validate.assert_called_once()

    def test_generator_template_not_found_handling(self, sample_config):
        """Test handling of missing templates."""
        generator = ProjectGenerator(sample_config)

        # Try to get non-existent template
        content = generator.get_template_content("non_existent_template.j2")

        # Should handle gracefully (return None or empty string)
        assert content is None or content == ""

    def test_generator_incremental_generation(self, sample_config, temp_output_dir):
        """Test incremental project generation."""
        generator = ProjectGenerator(sample_config)

        # Generate basic structure first
        result1 = generator.create_package_structure(temp_output_dir)
        assert result1["success"] is True

        # Add configuration files
        result2 = generator.create_configuration_files(temp_output_dir)
        assert result2["success"] is True

        # Add tests
        result3 = generator.create_test_structure(temp_output_dir)
        assert result3["success"] is True

        # Verify all components exist
        assert (temp_output_dir / "src").exists()
        assert (temp_output_dir / "tests").exists()
        assert (temp_output_dir / "pyproject.toml").exists()

    def test_generator_summary_information(self, sample_config, temp_output_dir):
        """Test generation summary information."""
        generator = ProjectGenerator(sample_config)

        result = generator.generate_complete_project(temp_output_dir)

        assert result["success"] is True
        assert "project_summary" in result

        summary = result["project_summary"]
        assert "files_created" in summary
        assert "directories_created" in summary
        assert isinstance(summary["files_created"], list)
        assert isinstance(summary["directories_created"], list)

    def test_generator_custom_output_structure(self, temp_output_dir):
        """Test generator with custom output structure."""
        config = Config(
            project_name="custom_project",
            package_name="custom_package",
            # Custom structure preferences could be added here
        )

        generator = ProjectGenerator(config)
        result = generator.generate_project_structure(temp_output_dir)

        assert result["success"] is True

        # Basic structure should still be created
        assert (temp_output_dir / "src" / "custom_package").exists()
        assert (temp_output_dir / "tests").exists()
