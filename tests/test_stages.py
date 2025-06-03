"""
Tests for the stage pipeline system.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from openpypi.core.config import Config
from openpypi.stages import (
    Pipeline,
    Stage,
    StageRegistry,
    StageResult,
    StageStatus,
    ValidationStage,
    register_stage,
    registry,
)


class TestStage:
    """Test the base Stage class."""

    def test_stage_initialization(self):
        """Test stage initialization."""

        class TestStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        stage = TestStage("test_stage")
        assert stage.name == "test_stage"
        assert stage.config == {}
        assert stage.dependencies == []
        assert not stage.is_async

    def test_stage_with_config(self):
        """Test stage initialization with configuration."""

        class TestStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        config = {"param1": "value1", "param2": "value2"}
        stage = TestStage("test_stage", config)
        assert stage.config == config

    def test_stage_dependencies(self):
        """Test stage dependencies."""

        class TestStage(Stage):
            def __init__(self, name: str, config: Dict[str, Any] = None):
                super().__init__(name, config)
                self.dependencies = ["dep1", "dep2"]

            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        stage = TestStage("test_stage")
        assert stage.get_dependencies() == ["dep1", "dep2"]

        # Test dependency validation
        assert not stage.validate_dependencies(["dep1"])  # Missing dep2
        assert stage.validate_dependencies(["dep1", "dep2"])  # All dependencies present
        assert stage.validate_dependencies(["dep1", "dep2", "extra"])  # Extra dependencies OK


class TestStageResult:
    """Test the StageResult class."""

    def test_stage_result_creation(self):
        """Test creating stage results."""
        result = StageResult(
            stage_name="test_stage",
            status=StageStatus.SUCCESS,
            message="Stage completed successfully",
        )

        assert result.stage_name == "test_stage"
        assert result.status == StageStatus.SUCCESS
        assert result.message == "Stage completed successfully"
        assert result.data == {}
        assert result.execution_time == 0.0

    def test_stage_result_with_data(self):
        """Test stage result with data."""
        data = {"output": "test_output", "files_created": ["file1.py", "file2.py"]}

        result = StageResult(stage_name="test_stage", status=StageStatus.SUCCESS, data=data)

        assert result.data == data

    def test_stage_result_with_error(self):
        """Test stage result with error."""
        error = Exception("Test error")

        result = StageResult(stage_name="test_stage", status=StageStatus.FAILED, error=error)

        assert result.error == error
        assert result.status == StageStatus.FAILED


class TestPipeline:
    """Test the Pipeline class."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = Pipeline("test_pipeline")
        assert pipeline.name == "test_pipeline"
        assert pipeline.stages == {}
        assert pipeline.stage_order == []
        assert pipeline.results == {}
        assert pipeline.context == {}

    def test_add_stage(self):
        """Test adding stages to pipeline."""

        class TestStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        pipeline = Pipeline("test_pipeline")
        stage1 = TestStage("stage1")
        stage2 = TestStage("stage2")

        pipeline.add_stage(stage1).add_stage(stage2)

        assert len(pipeline.stages) == 2
        assert "stage1" in pipeline.stages
        assert "stage2" in pipeline.stages
        assert pipeline.stage_order == ["stage1", "stage2"]

    def test_remove_stage(self):
        """Test removing stages from pipeline."""

        class TestStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        pipeline = Pipeline("test_pipeline")
        stage1 = TestStage("stage1")

        pipeline.add_stage(stage1)
        assert "stage1" in pipeline.stages

        pipeline.remove_stage("stage1")
        assert "stage1" not in pipeline.stages
        assert "stage1" not in pipeline.stage_order

    def test_set_context(self):
        """Test setting pipeline context."""
        pipeline = Pipeline("test_pipeline")
        context = {"key1": "value1", "key2": "value2"}

        pipeline.set_context(context)
        assert pipeline.context == context

        # Test updating context
        additional_context = {"key3": "value3"}
        pipeline.set_context(additional_context)
        assert pipeline.context["key1"] == "value1"  # Original keys preserved
        assert pipeline.context["key3"] == "value3"  # New key added

    def test_dependency_resolution(self):
        """Test dependency resolution in pipeline."""

        class TestStage(Stage):
            def __init__(self, name: str, dependencies: list = None):
                super().__init__(name)
                self.dependencies = dependencies or []

            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        pipeline = Pipeline("test_pipeline")

        # Create stages with dependencies
        stage1 = TestStage("stage1")  # No dependencies
        stage2 = TestStage("stage2", ["stage1"])  # Depends on stage1
        stage3 = TestStage("stage3", ["stage1", "stage2"])  # Depends on stage1 and stage2

        # Add stages in random order
        pipeline.add_stage(stage3).add_stage(stage1).add_stage(stage2)

        # Resolve dependencies
        execution_order = pipeline._resolve_dependencies()

        # stage1 should be first, then stage2, then stage3
        assert execution_order == ["stage1", "stage2", "stage3"]

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""

        class TestStage(Stage):
            def __init__(self, name: str, dependencies: list = None):
                super().__init__(name)
                self.dependencies = dependencies or []

            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        pipeline = Pipeline("test_pipeline")

        # Create circular dependency: stage1 -> stage2 -> stage1
        stage1 = TestStage("stage1", ["stage2"])
        stage2 = TestStage("stage2", ["stage1"])

        pipeline.add_stage(stage1).add_stage(stage2)

        with pytest.raises(RuntimeError, match="Circular dependency detected"):
            pipeline._resolve_dependencies()

    def test_pipeline_execution(self):
        """Test pipeline execution."""

        class TestStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    message=f"{self.name} completed",
                    data={f"{self.name}_output": f"output from {self.name}"},
                )

        pipeline = Pipeline("test_pipeline")
        stage1 = TestStage("stage1")
        stage2 = TestStage("stage2")

        pipeline.add_stage(stage1).add_stage(stage2)

        results = pipeline.execute()

        assert len(results) == 2
        assert "stage1" in results
        assert "stage2" in results

        # Check results
        assert results["stage1"].status == StageStatus.SUCCESS
        assert results["stage2"].status == StageStatus.SUCCESS

        # Check context was updated with stage results
        assert "stage1_result" in pipeline.context
        assert "stage2_result" in pipeline.context

    def test_pipeline_failure_handling(self):
        """Test pipeline failure handling."""

        class FailingStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(
                    stage_name=self.name, status=StageStatus.FAILED, message="Stage failed"
                )

        class SuccessStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(
                    stage_name=self.name, status=StageStatus.SUCCESS, message="Stage succeeded"
                )

        pipeline = Pipeline("test_pipeline")
        stage1 = SuccessStage("stage1")
        stage2 = FailingStage("stage2")
        stage3 = SuccessStage("stage3")

        pipeline.add_stage(stage1).add_stage(stage2).add_stage(stage3)

        results = pipeline.execute()

        # Should stop at failing stage by default
        assert len(results) == 2
        assert results["stage1"].status == StageStatus.SUCCESS
        assert results["stage2"].status == StageStatus.FAILED
        assert "stage3" not in results

    def test_pipeline_continue_on_failure(self):
        """Test pipeline continuing on failure."""

        class FailingStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(
                    stage_name=self.name, status=StageStatus.FAILED, message="Stage failed"
                )

        class SuccessStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(
                    stage_name=self.name, status=StageStatus.SUCCESS, message="Stage succeeded"
                )

        # Configure pipeline to continue on failure
        pipeline = Pipeline("test_pipeline", {"continue_on_failure": True})
        stage1 = SuccessStage("stage1")
        stage2 = FailingStage("stage2")
        stage3 = SuccessStage("stage3")

        pipeline.add_stage(stage1).add_stage(stage2).add_stage(stage3)

        results = pipeline.execute()

        # Should execute all stages
        assert len(results) == 3
        assert results["stage1"].status == StageStatus.SUCCESS
        assert results["stage2"].status == StageStatus.FAILED
        assert results["stage3"].status == StageStatus.SUCCESS

    def test_pipeline_summary(self):
        """Test pipeline execution summary."""

        class TestStage(Stage):
            def __init__(self, name: str, should_fail: bool = False):
                super().__init__(name)
                self.should_fail = should_fail

            def execute(self, context: Dict[str, Any]) -> StageResult:
                if self.should_fail:
                    return StageResult(
                        stage_name=self.name, status=StageStatus.FAILED, message="Stage failed"
                    )
                else:
                    return StageResult(
                        stage_name=self.name, status=StageStatus.SUCCESS, message="Stage succeeded"
                    )

        pipeline = Pipeline("test_pipeline", {"continue_on_failure": True})
        stage1 = TestStage("stage1")  # Success
        stage2 = TestStage("stage2", should_fail=True)  # Failure
        stage3 = TestStage("stage3")  # Success

        pipeline.add_stage(stage1).add_stage(stage2).add_stage(stage3)
        pipeline.execute()

        summary = pipeline.get_summary()

        assert summary["pipeline_name"] == "test_pipeline"
        assert summary["total_stages"] == 3
        assert summary["success_count"] == 2
        assert summary["failed_count"] == 1
        assert summary["skipped_count"] == 0
        assert summary["overall_status"] == "FAILED"  # Due to one failure


class TestValidationStage:
    """Test the ValidationStage implementation."""

    def test_validation_stage_initialization(self):
        """Test validation stage initialization."""
        stage = ValidationStage("validation")
        assert stage.name == "validation"
        assert stage.dependencies == []

    def test_validation_stage_success(self):
        """Test successful validation."""
        stage = ValidationStage("validation")

        # Create valid configuration
        config = Config(
            package_name="test_package",
            project_name="Test Project",
            author="Test Author",
            email="test@example.com",
            version="1.0.0",
            python_requires=">=3.8",
        )

        context = {"project_config": config, "output_dir": "/tmp/test"}

        with patch("pathlib.Path.parent") as mock_parent:
            mock_parent.exists.return_value = True
            mock_parent.is_dir.return_value = True

            result = stage.execute(context)

        assert result.status == StageStatus.SUCCESS
        assert "validated_config" in result.data
        assert "validation_results" in result.data

    def test_validation_stage_invalid_package_name(self):
        """Test validation with invalid package name."""
        stage = ValidationStage("validation")

        # Create configuration with invalid package name
        config = Config(
            package_name="123invalid",  # Invalid: starts with number
            project_name="Test Project",
            author="Test Author",
            email="test@example.com",
            version="1.0.0",
            python_requires=">=3.8",
        )

        context = {"project_config": config, "output_dir": "/tmp/test"}

        result = stage.execute(context)

        assert result.status == StageStatus.FAILED
        assert "package_name" in result.message

    def test_validation_stage_invalid_email(self):
        """Test validation with invalid email."""
        stage = ValidationStage("validation")

        config = Config(
            package_name="test_package",
            project_name="Test Project",
            author="Test Author",
            email="invalid-email",  # Invalid email format
            version="1.0.0",
            python_requires=">=3.8",
        )

        context = {"project_config": config, "output_dir": "/tmp/test"}

        result = stage.execute(context)

        assert result.status == StageStatus.FAILED
        assert "email" in result.message

    def test_validation_stage_invalid_version(self):
        """Test validation with invalid version."""
        stage = ValidationStage("validation")

        config = Config(
            package_name="test_package",
            project_name="Test Project",
            author="Test Author",
            email="test@example.com",
            version="invalid.version",  # Invalid semantic version
            python_requires=">=3.8",
        )

        context = {"project_config": config, "output_dir": "/tmp/test"}

        result = stage.execute(context)

        assert result.status == StageStatus.FAILED
        assert "version" in result.message

    def test_validation_stage_no_config(self):
        """Test validation with missing configuration."""
        stage = ValidationStage("validation")

        context = {}  # No project_config

        result = stage.execute(context)

        assert result.status == StageStatus.FAILED
        assert "No project configuration found" in result.message


class TestStageRegistry:
    """Test the stage registry."""

    def test_stage_registration(self):
        """Test registering stages."""
        test_registry = StageRegistry()

        @register_stage
        class TestStage(Stage):
            def execute(self, context: Dict[str, Any]) -> StageResult:
                return StageResult(stage_name=self.name, status=StageStatus.SUCCESS)

        # Should be registered in global registry - "TestStage" becomes "test"
        assert "test" in registry._stages

    def test_create_stage(self):
        """Test creating stage instances."""
        # Test with existing stage
        validation_stage = registry.create_stage("validation")
        assert isinstance(validation_stage, ValidationStage)

    def test_create_unknown_stage(self):
        """Test creating unknown stage raises error."""
        with pytest.raises(ValueError, match="Unknown stage"):
            registry.create_stage("unknown_stage")

    def test_list_stages(self):
        """Test listing all stages."""
        stages = registry.list_stages()
        assert isinstance(stages, list)
        assert "validation" in stages


class TestAsyncPipeline:
    """Test asynchronous pipeline execution."""

    @pytest.mark.asyncio
    async def test_async_pipeline_execution(self):
        """Test asynchronous pipeline execution."""

        class AsyncTestStage(Stage):
            def __init__(self, name: str, delay: float = 0.1):
                super().__init__(name)
                self.is_async = True
                self.delay = delay

            async def _execute_async_impl(self, context: Dict[str, Any]) -> StageResult:
                await asyncio.sleep(self.delay)
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    message=f"Async {self.name} completed",
                )

            def execute(self, context: Dict[str, Any]) -> StageResult:
                # Should not be called for async stages
                return StageResult(stage_name=self.name, status=StageStatus.FAILED)

        pipeline = Pipeline("async_pipeline")
        stage1 = AsyncTestStage("async_stage1", 0.1)
        stage2 = AsyncTestStage("async_stage2", 0.1)

        pipeline.add_stage(stage1).add_stage(stage2)

        start_time = datetime.now()
        results = await pipeline.execute_async()
        execution_time = (datetime.now() - start_time).total_seconds()

        # Check results
        assert len(results) == 2
        assert results["async_stage1"].status == StageStatus.SUCCESS
        assert results["async_stage2"].status == StageStatus.SUCCESS

        # Should take at least 0.2 seconds (two stages with 0.1s delay each)
        assert execution_time >= 0.2


@pytest.fixture
def sample_config():
    """Fixture for sample configuration."""
    return Config(
        package_name="test_package",
        project_name="Test Project",
        author="Test Author",
        email="test@example.com",
        version="1.0.0",
        python_requires=">=3.8",
    )


@pytest.fixture
def sample_context(sample_config):
    """Fixture for sample pipeline context."""
    return {"project_config": sample_config, "output_dir": "/tmp/test"}
