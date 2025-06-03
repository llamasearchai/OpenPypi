"""
Core orchestrator for managing the seven-stage package generation pipeline.
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from openpypi.core.context import PackageContext
from openpypi.providers.base import BaseProvider
from openpypi.stages.base import BaseStage
from openpypi.stages.p0_orchestrator import OrchestratorStage
from openpypi.stages.p1_conceptualizer import ConceptualizerStage
from openpypi.stages.p2_architect import ArchitectStage
from openpypi.stages.p3_packager import PackagerStage
from openpypi.stages.p4_validator import ValidatorStage
from openpypi.stages.p5_documentarian import DocumentarianStage
from openpypi.stages.p6_deployer import DeployerStage
from openpypi.stages.p7_refiner import RefinerStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the seven-stage package generation pipeline.

    This class manages the execution flow, error handling, progress tracking,
    and coordination between all stages of the package generation process.
    """

    def __init__(self, provider: BaseProvider):
        """Initialize the orchestrator with an AI provider."""
        self.provider = provider
        self.stages: List[Type[BaseStage]] = [
            OrchestratorStage,  # P0: Master orchestration and planning
            ConceptualizerStage,  # P1: Concept refinement and specification
            ArchitectStage,  # P2: Architecture design and planning
            PackagerStage,  # P3: Code generation and packaging
            ValidatorStage,  # P4: Testing and validation
            DocumentarianStage,  # P5: Documentation generation
            DeployerStage,  # P6: CI/CD and deployment setup
            RefinerStage,  # P7: Final refinement and quality assurance
        ]
        self.progress_callback: Optional[Callable[[int, str, str], None]] = None
        self.current_stage = 0
        self.total_stages = len(self.stages)

    def set_progress_callback(self, callback: Callable[[int, str, str], None]) -> None:
        """Set callback function for progress updates."""
        self.progress_callback = callback

    async def execute_pipeline(
        self, idea: str, output_dir: Optional[Path] = None, **kwargs
    ) -> PackageContext:
        """
        Execute the complete seven-stage pipeline.

        Args:
            idea: The initial package idea/description
            output_dir: Directory to create the package in
            **kwargs: Additional configuration options

        Returns:
            PackageContext: The final context with all stage outputs

        Raises:
            PipelineError: If any stage fails or validation errors occur
        """
        logger.info("Starting OpenPypi package generation pipeline")
        start_time = time.time()

        try:
            # Initialize context
            context = PackageContext(
                idea=idea, output_dir=output_dir or Path.cwd() / "generated_package", **kwargs
            )

            # Execute each stage
            for stage_index, stage_class in enumerate(self.stages):
                self.current_stage = stage_index
                stage_name = stage_class.__name__.replace("Stage", "")

                logger.info(f"Executing Stage {stage_index}: {stage_name}")

                # Update progress
                if self.progress_callback:
                    self.progress_callback(stage_index, f"Executing {stage_name}", "🔄 In Progress")

                # Create and execute stage
                stage_instance = stage_class(self.provider)

                try:
                    await stage_instance.execute(context)

                    # Update progress - success
                    if self.progress_callback:
                        self.progress_callback(
                            stage_index, f"Completed {stage_name}", "✅ Complete"
                        )

                    logger.info(f"Stage {stage_index} ({stage_name}) completed successfully")

                except Exception as stage_error:
                    # Update progress - error
                    if self.progress_callback:
                        self.progress_callback(stage_index, f"Failed {stage_name}", "❌ Failed")

                    logger.error(f"Stage {stage_index} ({stage_name}) failed: {stage_error}")

                    # Attempt recovery if possible
                    if await self._attempt_stage_recovery(stage_instance, context, stage_error):
                        logger.info(f"Stage {stage_index} recovered successfully")
                        if self.progress_callback:
                            self.progress_callback(
                                stage_index, f"Recovered {stage_name}", "🔄 Recovered"
                            )
                    else:
                        raise PipelineError(
                            f"Stage {stage_index} ({stage_name}) failed and could not be recovered: {stage_error}"
                        ) from stage_error

            # Pipeline completed successfully
            execution_time = time.time() - start_time
            logger.info(f"Pipeline completed successfully in {execution_time:.2f} seconds")

            # Final validation
            await self._validate_final_output(context)

            # Update final progress
            if self.progress_callback:
                self.progress_callback(self.total_stages, "Pipeline Complete", "🎉 Success")

            return context

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Pipeline failed after {execution_time:.2f} seconds: {e}")

            # Update progress - pipeline failed
            if self.progress_callback:
                self.progress_callback(self.current_stage, "Pipeline Failed", "💥 Error")

            raise PipelineError(f"Package generation pipeline failed: {e}") from e

    async def _attempt_stage_recovery(
        self, stage: BaseStage, context: PackageContext, error: Exception
    ) -> bool:
        """
        Attempt to recover from a stage failure.

        Args:
            stage: The failed stage instance
            context: Current package context
            error: The error that occurred

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        logger.info(f"Attempting recovery for stage: {stage.__class__.__name__}")

        # Check if stage supports recovery
        if not hasattr(stage, "attempt_recovery"):
            logger.warning(f"Stage {stage.__class__.__name__} does not support recovery")
            return False

        try:
            # Attempt stage-specific recovery
            recovery_successful = await stage.attempt_recovery(context, error)

            if recovery_successful:
                logger.info(f"Stage {stage.__class__.__name__} recovery successful")
                return True
            else:
                logger.warning(f"Stage {stage.__class__.__name__} recovery failed")
                return False

        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed: {recovery_error}")
            return False

    async def _validate_final_output(self, context: PackageContext) -> None:
        """
        Validate the final pipeline output.

        Args:
            context: The final package context

        Raises:
            PipelineError: If final validation fails
        """
        logger.info("Performing final pipeline validation")

        # Check that all stages completed
        required_stages = [
            "p0_orchestration",
            "p1_concept",
            "p2_architecture",
            "p3_package",
            "p4_validation",
            "p5_documentation",
            "p6_deployment",
            "p7_refinement",
        ]

        missing_stages = []
        for stage_key in required_stages:
            if not context.get_stage_output(stage_key):
                missing_stages.append(stage_key)

        if missing_stages:
            raise PipelineError(f"Missing outputs from stages: {missing_stages}")

        # Check that output directory exists and has content
        if not context.output_dir.exists():
            raise PipelineError(f"Output directory does not exist: {context.output_dir}")

        # Check for essential files
        essential_files = ["README.md", "pyproject.toml", "src", "tests"]

        missing_files = []
        for file_name in essential_files:
            file_path = context.output_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            raise PipelineError(f"Missing essential files/directories: {missing_files}")

        # Check final quality score
        refinement_output = context.get_stage_output("p7_refinement")
        if refinement_output:
            final_score = refinement_output.get("final_score", 0)
            if final_score < 60:  # Minimum acceptable quality threshold
                logger.warning(
                    f"Final quality score ({final_score}) below recommended threshold (60)"
                )
                # Don't fail the pipeline, but log the warning

        logger.info("Final pipeline validation completed successfully")

    async def execute_stage_subset(
        self, context: PackageContext, start_stage: int = 0, end_stage: Optional[int] = None
    ) -> PackageContext:
        """
        Execute a subset of the pipeline stages.

        Args:
            context: Current package context
            start_stage: Index of first stage to execute (0-based)
            end_stage: Index of last stage to execute (exclusive), None for all remaining

        Returns:
            PackageContext: Updated context after executing stages

        Raises:
            PipelineError: If any stage fails
        """
        if end_stage is None:
            end_stage = len(self.stages)

        if start_stage < 0 or start_stage >= len(self.stages):
            raise PipelineError(f"Invalid start_stage: {start_stage}")

        if end_stage <= start_stage or end_stage > len(self.stages):
            raise PipelineError(f"Invalid end_stage: {end_stage}")

        logger.info(f"Executing stages {start_stage} to {end_stage - 1}")

        for stage_index in range(start_stage, end_stage):
            stage_class = self.stages[stage_index]
            stage_name = stage_class.__name__.replace("Stage", "")

            logger.info(f"Executing Stage {stage_index}: {stage_name}")

            if self.progress_callback:
                self.progress_callback(stage_index, f"Executing {stage_name}", "🔄 In Progress")

            stage_instance = stage_class(self.provider)

            try:
                await stage_instance.execute(context)

                if self.progress_callback:
                    self.progress_callback(stage_index, f"Completed {stage_name}", "✅ Complete")

                logger.info(f"Stage {stage_index} ({stage_name}) completed successfully")

            except Exception as stage_error:
                if self.progress_callback:
                    self.progress_callback(stage_index, f"Failed {stage_name}", "❌ Failed")

                logger.error(f"Stage {stage_index} ({stage_name}) failed: {stage_error}")
                raise PipelineError(
                    f"Stage {stage_index} ({stage_name}) failed: {stage_error}"
                ) from stage_error

        return context

    async def get_pipeline_status(self, context: PackageContext) -> Dict[str, Any]:
        """
        Get the current status of the pipeline execution.

        Args:
            context: Package context to analyze

        Returns:
            Dict containing pipeline status information
        """
        status = {
            "total_stages": self.total_stages,
            "completed_stages": 0,
            "current_stage": self.current_stage,
            "stage_status": {},
            "overall_progress": 0.0,
            "estimated_time_remaining": None,
        }

        stage_names = [
            "orchestration",
            "conceptualization",
            "architecture",
            "packaging",
            "validation",
            "documentation",
            "deployment",
            "refinement",
        ]

        # Check completion status of each stage
        for i, stage_name in enumerate(stage_names):
            stage_key = f"p{i}_{stage_name}"
            stage_output = context.get_stage_output(stage_key)

            if stage_output:
                status["completed_stages"] += 1
                status["stage_status"][stage_name] = {
                    "completed": True,
                    "success": True,
                    "output_size": len(str(stage_output)),
                }
            else:
                status["stage_status"][stage_name] = {
                    "completed": False,
                    "success": False,
                    "output_size": 0,
                }

        # Calculate overall progress
        status["overall_progress"] = (status["completed_stages"] / status["total_stages"]) * 100

        return status

    async def create_checkpoint(self, context: PackageContext) -> Dict[str, Any]:
        """
        Create a checkpoint of the current pipeline state.

        Args:
            context: Current package context

        Returns:
            Dict containing checkpoint data
        """
        checkpoint = {
            "timestamp": time.time(),
            "current_stage": self.current_stage,
            "context_data": context.to_dict(),
            "pipeline_status": await self.get_pipeline_status(context),
        }

        # Save checkpoint to file
        checkpoint_path = context.output_dir / ".openpypi_checkpoint.json"
        import json

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, indent=2, default=str)

        logger.info(f"Created checkpoint at stage {self.current_stage}")
        return checkpoint

    async def restore_from_checkpoint(self, checkpoint_path: Path) -> PackageContext:
        """
        Restore pipeline state from a checkpoint.

        Args:
            checkpoint_path: Path to checkpoint file

        Returns:
            PackageContext: Restored context

        Raises:
            PipelineError: If checkpoint is invalid or cannot be restored
        """
        try:
            import json

            with open(checkpoint_path, "r") as f:
                checkpoint = json.load(f)

            # Restore context
            context = PackageContext.from_dict(checkpoint["context_data"])
            self.current_stage = checkpoint["current_stage"]

            logger.info(f"Restored checkpoint from stage {self.current_stage}")
            return context

        except Exception as e:
            raise PipelineError(f"Failed to restore checkpoint: {e}") from e

    def get_stage_info(self, stage_index: int) -> Dict[str, Any]:
        """
        Get information about a specific stage.

        Args:
            stage_index: Index of the stage (0-based)

        Returns:
            Dict containing stage information
        """
        if stage_index < 0 or stage_index >= len(self.stages):
            raise ValueError(f"Invalid stage index: {stage_index}")

        stage_class = self.stages[stage_index]

        return {
            "index": stage_index,
            "name": stage_class.__name__.replace("Stage", ""),
            "class_name": stage_class.__name__,
            "description": stage_class.__doc__ or "No description available",
            "module": stage_class.__module__,
        }

    def get_all_stages_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all pipeline stages.

        Returns:
            List of dicts containing stage information
        """
        return [self.get_stage_info(i) for i in range(len(self.stages))]


class PipelineError(Exception):
    """Exception raised when pipeline execution fails."""

    pass
