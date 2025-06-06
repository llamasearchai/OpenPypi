"""
Generation stage for code and project generation.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from ..core.config import Config
from ..core.generator import ProjectGenerator
from . import Stage, StageResult, StageStatus, register_stage

logger = logging.getLogger(__name__)


@register_stage
class GenerationStage(Stage):
    """Stage for generating project code and structure."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.dependencies = ["validation"]  # Depends on validation stage

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute generation stage."""
        try:
            logger.info("Starting generation stage")

            # Get validated configuration from context
            validated_config = context.get("validation_result", {}).get("validated_config")
            if not validated_config:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message="No validated configuration found in context",
                )

            # Get output directory
            output_dir = context.get("output_dir")
            if not output_dir:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message="No output directory specified",
                )

            # Create project generator
            generator = ProjectGenerator(validated_config)

            # Generate project
            project_path = Path(output_dir) / validated_config.project_name

            # Update generator config with the correct output directory
            generator.config.output_dir = Path(output_dir)
            generation_results = generator.generate()

            # Check if generation was successful (project_dir indicates success)
            if generation_results.get("project_dir"):
                actual_project_path = generation_results["project_dir"]
                logger.info(f"Project generated successfully at {actual_project_path}")
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    message=f"Project generated at {actual_project_path}",
                    data={
                        "project_path": actual_project_path,
                        "generation_results": generation_results,
                        "files_created": generation_results.get("files_created", []),
                        "directories_created": generation_results.get("directories_created", []),
                    },
                )
            else:
                error_msg = f"Project generation failed: {generation_results.get('error', 'No project directory created')}"
                logger.error(error_msg)
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=error_msg,
                    data={"generation_results": generation_results},
                )

        except Exception as e:
            logger.error(f"Generation stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                message=f"Generation stage error: {e}",
                error=e,
            )

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """Check if generation stage can execute."""
        # Need validated configuration and output directory
        validation_result = context.get("validation_result", {})
        validated_config = validation_result.get("validated_config")
        output_dir = context.get("output_dir")

        return validated_config is not None and output_dir is not None
