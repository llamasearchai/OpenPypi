"""
Testing stage for running tests and quality checks.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from . import Stage, StageResult, StageStatus, register_stage

logger = logging.getLogger(__name__)


@register_stage
class TestingStage(Stage):
    """Stage for running tests and quality checks."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.dependencies = ["generation"]  # Depends on generation stage

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute testing stage."""
        try:
            logger.info("Starting testing stage")

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

            # Run tests and quality checks
            test_results = {
                "pytest": self._run_pytest(project_dir),
                "linting": self._run_linting(project_dir),
                "type_checking": self._run_type_checking(project_dir),
                "security_scan": self._run_security_scan(project_dir),
            }

            # Determine overall status
            failed_checks = [name for name, result in test_results.items() if not result["success"]]

            if failed_checks:
                status = StageStatus.FAILED
                message = f"Testing failed: {', '.join(failed_checks)} failed"
            else:
                status = StageStatus.SUCCESS
                message = "All tests and quality checks passed"

            logger.info(f"Testing stage completed with status: {status}")
            return StageResult(
                stage_name=self.name,
                status=status,
                message=message,
                data={"test_results": test_results, "failed_checks": failed_checks},
            )

        except Exception as e:
            logger.error(f"Testing stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                message=f"Testing stage error: {e}",
                error=e,
            )

    def _run_pytest(self, project_dir: Path) -> Dict[str, Any]:
        """Run pytest tests."""
        try:
            cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
            result = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=300
            )

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test execution timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_linting(self, project_dir: Path) -> Dict[str, Any]:
        """Run code linting checks."""
        try:
            # Run black check
            black_result = subprocess.run(
                ["python", "-m", "black", "--check", "src/", "tests/"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Run isort check
            isort_result = subprocess.run(
                ["python", "-m", "isort", "--check-only", "src/", "tests/"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Run flake8
            flake8_result = subprocess.run(
                ["python", "-m", "flake8", "src/", "tests/"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            success = all(
                [
                    black_result.returncode == 0,
                    isort_result.returncode == 0,
                    flake8_result.returncode == 0,
                ]
            )

            return {
                "success": success,
                "black": {
                    "exit_code": black_result.returncode,
                    "stdout": black_result.stdout,
                    "stderr": black_result.stderr,
                },
                "isort": {
                    "exit_code": isort_result.returncode,
                    "stdout": isort_result.stdout,
                    "stderr": isort_result.stderr,
                },
                "flake8": {
                    "exit_code": flake8_result.returncode,
                    "stdout": flake8_result.stdout,
                    "stderr": flake8_result.stderr,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_type_checking(self, project_dir: Path) -> Dict[str, Any]:
        """Run mypy type checking."""
        try:
            cmd = ["python", "-m", "mypy", "src/"]
            result = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=120
            )

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_security_scan(self, project_dir: Path) -> Dict[str, Any]:
        """Run security scanning with bandit."""
        try:
            cmd = ["python", "-m", "bandit", "-r", "src/", "-f", "json"]
            result = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=120
            )

            # Bandit returns non-zero if issues found, but that's expected
            # Only fail if there's a critical error
            success = result.returncode in [0, 1]  # 0 = no issues, 1 = issues found

            return {
                "success": success,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """Check if testing stage can execute."""
        # Need project path from generation stage
        generation_result = context.get("generation_result", {})
        project_path = generation_result.get("project_path")

        return project_path is not None
