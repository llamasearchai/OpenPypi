"""
Stage pipeline system for multi-stage project processing.

This module provides a pipeline architecture for processing projects through
multiple stages: validation, generation, testing, packaging, and deployment.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class StageStatus(Enum):
    """Status of a stage execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of a stage execution."""

    stage_name: str
    status: StageStatus
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[Exception] = None


class Stage(ABC):
    """Base class for pipeline stages."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.dependencies: List[str] = []
        self.is_async = False

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute the stage synchronously."""
        pass

    async def execute_async(self, context: Dict[str, Any]) -> StageResult:
        """Execute the stage asynchronously."""
        if self.is_async:
            return await self._execute_async_impl(context)
        else:
            # Run synchronous execute in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.execute, context)

    async def _execute_async_impl(self, context: Dict[str, Any]) -> StageResult:
        """Implementation for async execution - override in async stages."""
        return self.execute(context)

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """Check if stage can execute given the current context."""
        return True

    def get_dependencies(self) -> List[str]:
        """Get list of stage dependencies."""
        return self.dependencies

    def validate_dependencies(self, completed_stages: List[str]) -> bool:
        """Validate that all dependencies have been completed."""
        return all(dep in completed_stages for dep in self.dependencies)


class Pipeline:
    """Pipeline for executing stages in order with dependency resolution."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.stages: Dict[str, Stage] = {}
        self.stage_order: List[str] = []
        self.results: Dict[str, StageResult] = {}
        self.context: Dict[str, Any] = {}
        self.is_async = False

    def add_stage(self, stage: Stage) -> "Pipeline":
        """Add a stage to the pipeline."""
        self.stages[stage.name] = stage
        if stage.name not in self.stage_order:
            self.stage_order.append(stage.name)
        return self

    def remove_stage(self, stage_name: str) -> "Pipeline":
        """Remove a stage from the pipeline."""
        if stage_name in self.stages:
            del self.stages[stage_name]
        if stage_name in self.stage_order:
            self.stage_order.remove(stage_name)
        return self

    def set_context(self, context: Dict[str, Any]) -> "Pipeline":
        """Set the pipeline context."""
        self.context.update(context)
        return self

    def _resolve_dependencies(self) -> List[str]:
        """Resolve stage execution order based on dependencies."""
        resolved = []
        remaining = list(self.stage_order)

        while remaining:
            progress_made = False

            for stage_name in remaining[:]:
                stage = self.stages[stage_name]
                if stage.validate_dependencies(resolved):
                    resolved.append(stage_name)
                    remaining.remove(stage_name)
                    progress_made = True

            if not progress_made:
                raise RuntimeError(f"Circular dependency detected in stages: {remaining}")

        return resolved

    def execute(self) -> Dict[str, StageResult]:
        """Execute all stages in the pipeline synchronously."""
        execution_order = self._resolve_dependencies()
        logger.info(f"Executing pipeline '{self.name}' with stages: {execution_order}")

        for stage_name in execution_order:
            stage = self.stages[stage_name]

            # Check if stage can execute
            if not stage.can_execute(self.context):
                result = StageResult(
                    stage_name=stage_name,
                    status=StageStatus.SKIPPED,
                    message="Stage skipped due to execution conditions",
                )
                self.results[stage_name] = result
                continue

            # Execute stage
            try:
                logger.info(f"Executing stage: {stage_name}")
                start_time = datetime.now()

                result = stage.execute(self.context)
                result.started_at = start_time
                result.completed_at = datetime.now()
                result.execution_time = (result.completed_at - result.started_at).total_seconds()

                self.results[stage_name] = result

                # Update context with stage results
                self.context[f"{stage_name}_result"] = result.data

                logger.info(f"Stage '{stage_name}' completed with status: {result.status}")

                # Stop execution if stage failed and not configured to continue
                if result.status == StageStatus.FAILED and not self.config.get(
                    "continue_on_failure", False
                ):
                    logger.error(f"Pipeline execution stopped due to failed stage: {stage_name}")
                    break

            except Exception as e:
                logger.error(f"Stage '{stage_name}' failed with exception: {e}")
                result = StageResult(
                    stage_name=stage_name,
                    status=StageStatus.FAILED,
                    message=str(e),
                    error=e,
                    started_at=start_time,
                    completed_at=datetime.now(),
                )
                self.results[stage_name] = result

                if not self.config.get("continue_on_failure", False):
                    break

        return self.results

    async def execute_async(self) -> Dict[str, StageResult]:
        """Execute all stages in the pipeline asynchronously."""
        execution_order = self._resolve_dependencies()
        logger.info(
            f"Executing pipeline '{self.name}' asynchronously with stages: {execution_order}"
        )

        for stage_name in execution_order:
            stage = self.stages[stage_name]

            # Check if stage can execute
            if not stage.can_execute(self.context):
                result = StageResult(
                    stage_name=stage_name,
                    status=StageStatus.SKIPPED,
                    message="Stage skipped due to execution conditions",
                )
                self.results[stage_name] = result
                continue

            # Execute stage
            try:
                logger.info(f"Executing stage: {stage_name}")
                start_time = datetime.now()

                result = await stage.execute_async(self.context)
                result.started_at = start_time
                result.completed_at = datetime.now()
                result.execution_time = (result.completed_at - result.started_at).total_seconds()

                self.results[stage_name] = result

                # Update context with stage results
                self.context[f"{stage_name}_result"] = result.data

                logger.info(f"Stage '{stage_name}' completed with status: {result.status}")

                # Stop execution if stage failed and not configured to continue
                if result.status == StageStatus.FAILED and not self.config.get(
                    "continue_on_failure", False
                ):
                    logger.error(f"Pipeline execution stopped due to failed stage: {stage_name}")
                    break

            except Exception as e:
                logger.error(f"Stage '{stage_name}' failed with exception: {e}")
                result = StageResult(
                    stage_name=stage_name,
                    status=StageStatus.FAILED,
                    message=str(e),
                    error=e,
                    started_at=start_time,
                    completed_at=datetime.now(),
                )
                self.results[stage_name] = result

                if not self.config.get("continue_on_failure", False):
                    break

        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get pipeline execution summary."""
        total_stages = len(self.results)
        success_count = sum(1 for r in self.results.values() if r.status == StageStatus.SUCCESS)
        failed_count = sum(1 for r in self.results.values() if r.status == StageStatus.FAILED)
        skipped_count = sum(1 for r in self.results.values() if r.status == StageStatus.SKIPPED)

        total_time = sum(r.execution_time for r in self.results.values())

        return {
            "pipeline_name": self.name,
            "total_stages": total_stages,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "total_execution_time": total_time,
            "overall_status": "SUCCESS" if failed_count == 0 else "FAILED",
            "stage_results": {
                name: {
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "message": result.message,
                }
                for name, result in self.results.items()
            },
        }


class StageRegistry:
    """Registry for managing pipeline stages."""

    def __init__(self):
        self._stages: Dict[str, Type[Stage]] = {}

    def register(self, stage_class: Type[Stage]) -> None:
        """Register a stage class."""
        stage_name = stage_class.__name__.lower().replace("stage", "")
        self._stages[stage_name] = stage_class
        logger.info(f"Registered stage: {stage_name}")

    def create_stage(self, name: str, config: Optional[Dict[str, Any]] = None) -> Stage:
        """Create a stage instance by name."""
        if name not in self._stages:
            raise ValueError(f"Unknown stage: {name}")

        return self._stages[name](name, config)

    def list_stages(self) -> List[str]:
        """List all registered stages."""
        return list(self._stages.keys())


# Global stage registry
registry = StageRegistry()


def register_stage(stage_class: Type[Stage]) -> Type[Stage]:
    """Decorator to register a stage."""
    registry.register(stage_class)
    return stage_class


from .deployment import DeploymentStage
from .generation import GenerationStage
from .packaging import PackagingStage
from .testing import TestingStage

# Import and register built-in stages
from .validation import ValidationStage

__all__ = [
    "Stage",
    "Pipeline",
    "StageResult",
    "StageStatus",
    "StageRegistry",
    "registry",
    "register_stage",
    "ValidationStage",
    "GenerationStage",
    "TestingStage",
    "PackagingStage",
    "DeploymentStage",
]
