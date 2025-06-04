"""
Packaging stage for building and packaging the project.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from . import Stage, StageResult, StageStatus, register_stage

logger = logging.getLogger(__name__)


@register_stage
class PackagingStage(Stage):
    """Stage for packaging and building the project."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.dependencies = ["generation"]  # Depends on generation stage

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute packaging stage."""
        try:
            logger.info("Starting packaging stage")

            # Get project path from generation results
            generation_result = context.get("generation_result", {})
            project_path = generation_result.get("project_path")

            if not project_path:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message="No project path found in generation results",
                )

            project_dir = Path(project_path)
            if not project_dir.exists():
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"Project directory does not exist: {project_path}",
                )

            # Build package
            build_results = self._build_package(project_dir)

            if build_results["success"]:
                status = StageStatus.SUCCESS
                message = "Package built successfully"
            else:
                status = StageStatus.FAILED
                message = f"Package build failed: {build_results.get('error', 'Unknown error')}"

            logger.info(f"Packaging stage completed with status: {status}")
            return StageResult(
                stage_name=self.name,
                status=status,
                message=message,
                data={"build_results": build_results},
            )

        except Exception as e:
            logger.error(f"Packaging stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                message=f"Packaging stage error: {e}",
                error=e,
            )

    def _build_package(self, project_dir: Path) -> Dict[str, Any]:
        """Build the Python package."""
        try:
            # Clean previous builds
            build_dir = project_dir / "build"
            dist_dir = project_dir / "dist"

            if build_dir.exists():
                import shutil

                shutil.rmtree(build_dir)

            if dist_dir.exists():
                import shutil

                shutil.rmtree(dist_dir)

            # Build package
            cmd = ["python", "-m", "build"]
            result = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=300
            )

            # Check if build was successful
            if result.returncode == 0:
                # List generated files
                dist_files = list(dist_dir.glob("*")) if dist_dir.exists() else []

                return {
                    "success": True,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "dist_files": [str(f.name) for f in dist_files],
                }
            else:
                return {
                    "success": False,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "error": "Build command failed",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Build process timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """Check if packaging stage can execute."""
        # Need project path from generation stage
        generation_result = context.get("generation_result", {})
        project_path = generation_result.get("project_path")

        return project_path is not None
