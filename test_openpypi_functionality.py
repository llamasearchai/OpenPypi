#!/usr/bin/env python3
"""
Test script to verify OpenPypi functionality.
"""

import shutil
import tempfile
from pathlib import Path

from openpypi import Config, OpenPypi


def test_openpypi_functionality():
    """Test basic OpenPypi functionality."""
    print("Testing OpenPypi basic functionality...")

    # Create a test config
    config = Config(
        project_name="test_project",
        package_name="test_package",
        author="Test Author",
        email="test@example.com",
        use_fastapi=True,
        use_docker=True,
        use_openai=True,
    )

    # Create OpenPypi instance
    openpypi = OpenPypi(config)

    # Test configuration validation
    try:
        openpypi.validate_config()
        print("SUCCESS: Configuration validation passed")
    except Exception as e:
        print(f"FAILED: Configuration validation failed: {e}")
        return False

    # Test project generation in a temp directory
    temp_dir = Path(tempfile.mkdtemp())
    try:
        config.output_dir = temp_dir
        result = openpypi.generate_project()

        if result["success"]:
            print("SUCCESS: Project generation successful")
            print(f'   Files created: {len(result["files_created"])}')
            print(f'   Directories created: {len(result["directories_created"])}')

            # Get project directory from pipeline results
            pipeline_results = result.get("pipeline_results", {})
            generation_result = pipeline_results.get("generation", {})
            project_path = (
                generation_result.data.get("project_path") if generation_result.data else None
            )

            if project_path:
                project_dir = Path(project_path)
                key_files = [
                    project_dir / "pyproject.toml",
                    project_dir / "README.md",
                    project_dir / "src" / "test_package" / "__init__.py",
                    project_dir / "tests" / "__init__.py",
                ]

                missing_files = [f for f in key_files if not f.exists()]
                if missing_files:
                    print(f"FAILED: Missing key files: {missing_files}")
                    return False
                else:
                    print("SUCCESS: All key files created successfully")
            else:
                print("WARNING: Could not verify file creation (no project path found)")

        else:
            print("FAILED: Project generation failed")
            return False

    except Exception as e:
        print(f"ERROR: Project generation error: {e}")
        return False
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    print("SUCCESS: OpenPypi basic functionality test completed successfully")
    return True


if __name__ == "__main__":
    success = test_openpypi_functionality()
    exit(0 if success else 1)
