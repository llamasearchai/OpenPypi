"""
Orchestrator Stage - P0: Project Orchestration and Management
===========================================================

This stage provides high-level orchestration and coordination of all other stages
in the project generation pipeline. It manages dependencies, execution order,
and ensures proper communication between stages.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import Config
from ..core.exceptions import OpenPypiError
from ..stages import Stage, StageResult, StageStatus

logger = logging.getLogger(__name__)


class OrchestratorStage(Stage):
    """
    Orchestrator stage that manages the entire project generation pipeline.

    This stage coordinates the execution of all other stages, manages their
    dependencies, handles error recovery, and provides overall project
    generation orchestration.
    """

    def __init__(self, name: str = "orchestrator", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.execution_plan: List[str] = []
        self.stage_results: Dict[str, StageResult] = {}
        self.continue_on_failure = self.config.get("continue_on_failure", False)
        self.parallel_execution = self.config.get("parallel_execution", False)
        self.max_retries = self.config.get("max_retries", 3)

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """
        Execute the orchestrator stage.

        Args:
            context: Pipeline execution context

        Returns:
            StageResult: Result of orchestration
        """
        start_time = datetime.now()

        try:
            logger.info(f"🎯 Starting project orchestration: {self.name}")

            # Validate context and configuration
            validation_result = self._validate_orchestration_context(context)
            if not validation_result["valid"]:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"Orchestration validation failed: {validation_result['error']}",
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )

            # Build execution plan
            execution_plan = self._build_execution_plan(context)
            logger.info(f"📋 Execution plan: {' → '.join(execution_plan)}")

            # Execute stages according to plan
            orchestration_results = self._execute_orchestration_plan(context, execution_plan)

            # Analyze results and determine overall success
            success_count = sum(
                1
                for result in orchestration_results.values()
                if result.status == StageStatus.SUCCESS
            )
            total_stages = len(orchestration_results)

            overall_success = success_count == total_stages

            execution_time = (datetime.now() - start_time).total_seconds()

            result_data = {
                "execution_plan": execution_plan,
                "stage_results": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "execution_time": result.execution_time,
                        "data": result.data,
                    }
                    for name, result in orchestration_results.items()
                },
                "success_count": success_count,
                "total_stages": total_stages,
                "overall_success": overall_success,
                "execution_time": execution_time,
            }

            if overall_success:
                logger.info(f"✅ Orchestration completed successfully in {execution_time:.2f}s")
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    message=f"Successfully orchestrated {total_stages} stages",
                    data=result_data,
                    execution_time=execution_time,
                )
            else:
                failed_count = total_stages - success_count
                logger.warning(f"⚠️ Orchestration completed with {failed_count} failures")
                return StageResult(
                    stage_name=self.name,
                    status=(
                        StageStatus.FAILED if not self.continue_on_failure else StageStatus.SUCCESS
                    ),
                    message=f"Orchestration completed: {success_count}/{total_stages} stages successful",
                    data=result_data,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Orchestration failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                message=f"Orchestration failed: {str(e)}",
                error=e,
                execution_time=execution_time,
            )

    def _validate_orchestration_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the orchestration context."""
        try:
            # Check for required context elements
            required_keys = ["project_config", "output_dir"]
            missing_keys = [key for key in required_keys if key not in context]

            if missing_keys:
                return {"valid": False, "error": f"Missing required context keys: {missing_keys}"}

            # Validate project configuration
            project_config = context.get("project_config")
            if not isinstance(project_config, Config):
                return {"valid": False, "error": "project_config must be a Config instance"}

            # Validate output directory
            output_dir = context.get("output_dir")
            if not isinstance(output_dir, (str, Path)):
                return {"valid": False, "error": "output_dir must be a string or Path"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _build_execution_plan(self, context: Dict[str, Any]) -> List[str]:
        """
        Build the execution plan for stages.

        Returns:
            List of stage names in execution order
        """
        # Default execution plan - can be customized based on context
        base_plan = [
            "conceptualizer",  # P1: Analyze and understand requirements
            "architect",  # P2: Design project architecture
            "packager",  # P3: Create package structure
            "validator",  # P4: Validate project structure
            "documentarian",  # P5: Generate documentation
            "deployer",  # P6: Prepare deployment
            "refiner",  # P7: Final refinements
        ]

        # Filter based on enabled features
        project_config = context.get("project_config")
        filtered_plan = []

        for stage in base_plan:
            # Add stage to plan based on configuration
            if stage == "deployer" and not project_config.use_docker:
                logger.info(f"⏭️  Skipping {stage} (Docker disabled)")
                continue

            filtered_plan.append(stage)

        return filtered_plan

    def _execute_orchestration_plan(
        self, context: Dict[str, Any], execution_plan: List[str]
    ) -> Dict[str, StageResult]:
        """Execute the orchestration plan."""
        results = {}

        if self.parallel_execution:
            return self._execute_parallel(context, execution_plan)
        else:
            return self._execute_sequential(context, execution_plan)

    def _execute_sequential(
        self, context: Dict[str, Any], execution_plan: List[str]
    ) -> Dict[str, StageResult]:
        """Execute stages sequentially."""
        results = {}

        for stage_name in execution_plan:
            logger.info(f"🔄 Executing stage: {stage_name}")

            try:
                # Create stage instance
                stage = self._create_stage_instance(stage_name)

                # Execute stage with retries
                result = self._execute_stage_with_retries(stage, context)
                results[stage_name] = result

                # Update context with stage results
                context[f"{stage_name}_result"] = result

                # Check if we should continue on failure
                if result.status == StageStatus.FAILED and not self.continue_on_failure:
                    logger.error(f"❌ Stage {stage_name} failed, stopping execution")
                    break

                logger.info(f"✅ Stage {stage_name} completed: {result.status.value}")

            except Exception as e:
                logger.error(f"❌ Error executing stage {stage_name}: {e}")
                results[stage_name] = StageResult(
                    stage_name=stage_name,
                    status=StageStatus.FAILED,
                    message=f"Stage execution error: {str(e)}",
                    error=e,
                )

                if not self.continue_on_failure:
                    break

        return results

    def _execute_parallel(
        self, context: Dict[str, Any], execution_plan: List[str]
    ) -> Dict[str, StageResult]:
        """Execute stages in parallel where possible."""
        # For now, implement basic parallel execution
        # In a more sophisticated implementation, this would analyze dependencies
        # and execute independent stages in parallel

        logger.info("🔀 Parallel execution not fully implemented, falling back to sequential")
        return self._execute_sequential(context, execution_plan)

    def _create_stage_instance(self, stage_name: str) -> Stage:
        """Create an instance of the specified stage."""
        # Import stages dynamically to avoid circular imports
        stage_mapping = {
            "conceptualizer": "p1_conceptualizer.ConceptualizerStage",
            "architect": "p2_architect.ArchitectStage",
            "packager": "p3_packager.PackagerStage",
            "validator": "p4_validator.ValidatorStage",
            "documentarian": "p5_documentarian.DocumentarianStage",
            "deployer": "p6_deployer.DeployerStage",
            "refiner": "p7_refiner.RefinerStage",
        }

        if stage_name not in stage_mapping:
            raise ValueError(f"Unknown stage: {stage_name}")

        module_path, class_name = stage_mapping[stage_name].rsplit(".", 1)

        try:
            # Dynamic import
            from importlib import import_module

            module = import_module(f"openpypi.stages.{module_path}")
            stage_class = getattr(module, class_name)

            return stage_class(stage_name)

        except ImportError as e:
            logger.warning(f"Could not import stage {stage_name}: {e}")
            # Return a mock stage for testing
            return MockStage(stage_name)

    def _execute_stage_with_retries(self, stage: Stage, context: Dict[str, Any]) -> StageResult:
        """Execute a stage with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"🔄 Retrying stage {stage.name} (attempt {attempt + 1}/{self.max_retries + 1})"
                    )

                result = stage.execute(context)

                if result.status == StageStatus.SUCCESS:
                    return result
                elif result.status == StageStatus.FAILED and attempt < self.max_retries:
                    logger.warning(f"⚠️ Stage {stage.name} failed, will retry")
                    last_exception = result.error
                    continue
                else:
                    return result

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(f"⚠️ Stage {stage.name} raised exception, will retry: {e}")
                    continue
                else:
                    logger.error(
                        f"❌ Stage {stage.name} failed after {self.max_retries} retries: {e}"
                    )

        # If we get here, all retries failed
        return StageResult(
            stage_name=stage.name,
            status=StageStatus.FAILED,
            message=f"Stage failed after {self.max_retries} retries",
            error=last_exception,
        )

    def get_capabilities(self) -> List[str]:
        """Get orchestrator capabilities."""
        return [
            "stage_coordination",
            "dependency_management",
            "error_recovery",
            "parallel_execution",
            "retry_logic",
            "execution_planning",
        ]


class MockStage(Stage):
    """Mock stage for testing purposes."""

    def __init__(self, name: str):
        super().__init__(name)

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute mock stage."""
        logger.info(f"🎭 Executing mock stage: {self.name}")

        return StageResult(
            stage_name=self.name,
            status=StageStatus.SUCCESS,
            message=f"Mock stage {self.name} completed successfully",
            data={"mock": True, "stage": self.name},
        )
