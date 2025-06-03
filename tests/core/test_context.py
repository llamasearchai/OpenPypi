"""
Tests for openpypi.core.context module.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from openpypi.core.config import Config
from openpypi.core.context import Context, ContextManager


class TestContext:
    """Test the Context class."""

    def test_context_initialization(self):
        """Test context initialization."""
        context = Context()
        assert isinstance(context.data, dict)
        assert len(context.data) == 0
        assert context.get_all() == {}

    def test_context_with_initial_data(self):
        """Test context initialization with data."""
        initial_data = {"key1": "value1", "key2": "value2"}
        context = Context(initial_data)

        assert context.get("key1") == "value1"
        assert context.get("key2") == "value2"
        assert len(context.data) == 2

    def test_context_set_get(self):
        """Test setting and getting values."""
        context = Context()

        context.set("test_key", "test_value")
        assert context.get("test_key") == "test_value"
        assert context.get("non_existent") is None
        assert context.get("non_existent", "default") == "default"

    def test_context_has(self):
        """Test checking if context has keys."""
        context = Context()
        context.set("existing_key", "value")

        assert context.has("existing_key") is True
        assert context.has("non_existent_key") is False

    def test_context_remove(self):
        """Test removing values from context."""
        context = Context()
        context.set("to_remove", "value")

        assert context.has("to_remove") is True
        context.remove("to_remove")
        assert context.has("to_remove") is False

        # Removing non-existent key should not raise error
        context.remove("non_existent")

    def test_context_update(self):
        """Test updating context with dictionary."""
        context = Context({"existing": "value"})

        update_data = {"new_key": "new_value", "existing": "updated_value"}
        context.update(update_data)

        assert context.get("new_key") == "new_value"
        assert context.get("existing") == "updated_value"

    def test_context_clear(self):
        """Test clearing context."""
        context = Context({"key1": "value1", "key2": "value2"})
        assert len(context.data) == 2

        context.clear()
        assert len(context.data) == 0
        assert context.get_all() == {}

    def test_context_get_all(self):
        """Test getting all context data."""
        data = {"key1": "value1", "key2": "value2"}
        context = Context(data)

        all_data = context.get_all()
        assert all_data == data
        assert all_data is not context.data  # Should be a copy

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        data = {"key1": "value1", "key2": "value2"}
        context = Context(data)

        dict_data = context.to_dict()
        assert dict_data == data
        assert dict_data is not context.data  # Should be a copy

    def test_context_from_dict(self):
        """Test creating context from dictionary."""
        data = {"key1": "value1", "key2": "value2"}
        context = Context.from_dict(data)

        assert context.get("key1") == "value1"
        assert context.get("key2") == "value2"

    def test_context_merge(self):
        """Test merging contexts."""
        context1 = Context({"key1": "value1", "shared": "original"})
        context2 = Context({"key2": "value2", "shared": "updated"})

        merged = context1.merge(context2)

        assert merged.get("key1") == "value1"
        assert merged.get("key2") == "value2"
        assert merged.get("shared") == "updated"  # Second context should override

        # Original contexts should be unchanged
        assert context1.get("shared") == "original"
        assert not context1.has("key2")

    def test_context_copy(self):
        """Test copying context."""
        original = Context({"key1": "value1", "key2": "value2"})
        copied = original.copy()

        assert copied.get_all() == original.get_all()
        assert copied.data is not original.data

        # Modifying copy should not affect original
        copied.set("key3", "value3")
        assert not original.has("key3")

    def test_context_nested_values(self):
        """Test context with nested values."""
        nested_data = {
            "config": {"debug": True, "timeout": 30},
            "paths": {"input": "/input", "output": "/output"},
        }

        context = Context(nested_data)

        assert context.get("config")["debug"] is True
        assert context.get("paths")["input"] == "/input"

    def test_context_path_operations(self):
        """Test context operations with Path objects."""
        context = Context()
        test_path = Path("/test/path")

        context.set("path_key", test_path)
        retrieved_path = context.get("path_key")

        assert isinstance(retrieved_path, Path)
        assert str(retrieved_path) == "/test/path"


class TestContextManager:
    """Test the ContextManager class."""

    def test_context_manager_initialization(self):
        """Test context manager initialization."""
        manager = ContextManager()
        assert isinstance(manager.context, Context)
        assert len(manager.context.data) == 0

    def test_context_manager_with_initial_context(self):
        """Test context manager with initial context."""
        initial_context = Context({"key": "value"})
        manager = ContextManager(initial_context)

        assert manager.context.get("key") == "value"

    def test_context_manager_create_project_context(self):
        """Test creating project context."""
        config = Config(
            project_name="test_project", package_name="test_package", author="Test Author"
        )
        output_dir = Path("/test/output")

        manager = ContextManager()
        context = manager.create_project_context(config, output_dir)

        assert context.get("project_config") == config
        assert context.get("output_dir") == output_dir
        assert context.get("project_name") == "test_project"
        assert context.get("package_name") == "test_package"
        assert context.get("author") == "Test Author"

    def test_context_manager_add_stage_result(self):
        """Test adding stage results to context."""
        manager = ContextManager()

        # Mock stage result
        stage_result = Mock()
        stage_result.status = "SUCCESS"
        stage_result.data = {"files_created": ["file1.py", "file2.py"]}
        stage_result.execution_time = 1.5

        manager.add_stage_result("test_stage", stage_result)

        assert manager.context.has("test_stage_result")
        result_data = manager.context.get("test_stage_result")
        assert result_data.status == "SUCCESS"
        assert result_data.data["files_created"] == ["file1.py", "file2.py"]

    def test_context_manager_get_stage_result(self):
        """Test getting stage results from context."""
        manager = ContextManager()

        # Add a stage result
        stage_result = Mock()
        stage_result.status = "SUCCESS"
        manager.add_stage_result("test_stage", stage_result)

        # Retrieve it
        retrieved = manager.get_stage_result("test_stage")
        assert retrieved == stage_result

        # Non-existent stage should return None
        assert manager.get_stage_result("non_existent") is None

    def test_context_manager_update_from_config(self):
        """Test updating context from config."""
        config = Config(project_name="config_project", version="2.0.0", use_docker=True)

        manager = ContextManager()
        manager.update_from_config(config)

        assert manager.context.get("project_name") == "config_project"
        assert manager.context.get("version") == "2.0.0"
        assert manager.context.get("use_docker") is True

    def test_context_manager_set_paths(self):
        """Test setting path information in context."""
        manager = ContextManager()

        paths = {
            "output_dir": Path("/output"),
            "src_dir": Path("/output/src"),
            "tests_dir": Path("/output/tests"),
        }

        manager.set_paths(paths)

        assert manager.context.get("output_dir") == Path("/output")
        assert manager.context.get("src_dir") == Path("/output/src")
        assert manager.context.get("tests_dir") == Path("/output/tests")

    def test_context_manager_validate_context(self):
        """Test context validation."""
        manager = ContextManager()

        # Empty context should be invalid
        assert not manager.validate_context()

        # Add required fields
        config = Config(project_name="test", package_name="test")
        manager.context.set("project_config", config)
        manager.context.set("output_dir", Path("/test"))

        assert manager.validate_context()

    def test_context_manager_get_context_summary(self):
        """Test getting context summary."""
        manager = ContextManager()

        config = Config(project_name="summary_test", version="1.0.0")
        manager.context.set("project_config", config)
        manager.context.set("output_dir", Path("/test"))
        manager.context.set("custom_key", "custom_value")

        summary = manager.get_context_summary()

        assert "project_name" in summary
        assert "version" in summary
        assert "output_dir" in summary
        assert summary["project_name"] == "summary_test"
        assert summary["version"] == "1.0.0"

    def test_context_manager_reset(self):
        """Test resetting context manager."""
        manager = ContextManager()
        manager.context.set("test_key", "test_value")

        assert manager.context.has("test_key")

        manager.reset()

        assert not manager.context.has("test_key")
        assert len(manager.context.data) == 0


class TestContextIntegration:
    """Test context integration scenarios."""

    def test_context_pipeline_simulation(self):
        """Test context through a simulated pipeline."""
        # Initialize context manager
        manager = ContextManager()

        # Create project context
        config = Config(
            project_name="pipeline_test", package_name="pipeline_package", author="Pipeline Author"
        )
        output_dir = Path("/pipeline/output")

        context = manager.create_project_context(config, output_dir)

        # Simulate stage 1: Conceptualizer
        stage1_result = Mock()
        stage1_result.status = "SUCCESS"
        stage1_result.data = {"concept": "Generated project concept"}
        manager.add_stage_result("conceptualizer", stage1_result)

        # Simulate stage 2: Architect
        stage2_result = Mock()
        stage2_result.status = "SUCCESS"
        stage2_result.data = {"architecture": "Project architecture defined"}
        manager.add_stage_result("architect", stage2_result)

        # Verify context contains all information
        assert manager.context.get("project_name") == "pipeline_test"
        assert manager.get_stage_result("conceptualizer") == stage1_result
        assert manager.get_stage_result("architect") == stage2_result

        # Get summary
        summary = manager.get_context_summary()
        assert "project_name" in summary
        assert summary["project_name"] == "pipeline_test"

    def test_context_error_handling(self):
        """Test context behavior with error conditions."""
        context = Context()

        # Test getting non-existent nested keys
        assert context.get("non.existent.key") is None

        # Test removing non-existent keys
        context.remove("non_existent")  # Should not raise

        # Test updating with None
        context.update(None)  # Should handle gracefully
        assert context.get_all() == {}

    def test_context_with_complex_data_types(self):
        """Test context with complex data types."""
        context = Context()

        # Set various data types
        context.set("string", "test_string")
        context.set("integer", 42)
        context.set("float", 3.14)
        context.set("boolean", True)
        context.set("list", [1, 2, 3])
        context.set("dict", {"nested": "value"})
        context.set("none", None)

        # Verify all types are preserved
        assert context.get("string") == "test_string"
        assert context.get("integer") == 42
        assert context.get("float") == 3.14
        assert context.get("boolean") is True
        assert context.get("list") == [1, 2, 3]
        assert context.get("dict")["nested"] == "value"
        assert context.get("none") is None
