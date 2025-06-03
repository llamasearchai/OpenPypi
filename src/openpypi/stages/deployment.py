"""
Deployment stage for deploying the project.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from ..providers import registry as provider_registry
from . import Stage, StageResult, StageStatus, register_stage

logger = logging.getLogger(__name__)


@register_stage
class DeploymentStage(Stage):
    """Stage for deploying the project."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.dependencies = ["packaging"]  # Depends on packaging stage

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute deployment stage."""
        try:
            logger.info("Starting deployment stage")

            # Get project path and configuration
            generation_result = context.get("generation_result", {})
            project_path = generation_result.get("project_path")

            if not project_path:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message="No project path found in generation results",
                )

            # Get deployment configuration
            deployment_config = self.config.get("deployment", {})
            deployment_type = deployment_config.get("type", "docker")

            # Perform deployment based on type
            if deployment_type == "docker":
                deployment_results = self._deploy_docker(project_path, deployment_config)
            elif deployment_type == "kubernetes":
                deployment_results = self._deploy_kubernetes(project_path, deployment_config)
            elif deployment_type == "cloud":
                deployment_results = self._deploy_cloud(project_path, deployment_config)
            else:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"Unknown deployment type: {deployment_type}",
                )

            if deployment_results["success"]:
                status = StageStatus.SUCCESS
                message = f"Deployment to {deployment_type} successful"
            else:
                status = StageStatus.FAILED
                message = f"Deployment to {deployment_type} failed: {deployment_results.get('error', 'Unknown error')}"

            logger.info(f"Deployment stage completed with status: {status}")
            return StageResult(
                stage_name=self.name,
                status=status,
                message=message,
                data={"deployment_results": deployment_results},
            )

        except Exception as e:
            logger.error(f"Deployment stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                message=f"Deployment stage error: {e}",
                error=e,
            )

    def _deploy_docker(self, project_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy using Docker."""
        try:
            # Get Docker provider
            docker_provider = provider_registry.get_provider("docker")

            if not docker_provider.validate_connection():
                return {"success": False, "error": "Docker daemon not available"}

            project_dir = Path(project_path)

            # Build Docker image
            tag = config.get("tag", f"{project_dir.name}:latest")
            build_result = docker_provider.build_image(
                dockerfile_path="Dockerfile", tag=tag, build_context=str(project_dir)
            )

            if not build_result["success"]:
                return {
                    "success": False,
                    "error": f"Docker build failed: {build_result.get('error')}",
                    "build_result": build_result,
                }

            # Run container if requested
            run_container = config.get("run_container", False)
            container_result = None

            if run_container:
                container_config = config.get("container", {})
                container_result = docker_provider.run_container(
                    image=tag,
                    name=container_config.get("name"),
                    ports=container_config.get("ports"),
                    environment=container_config.get("environment"),
                )

            return {
                "success": True,
                "deployment_type": "docker",
                "image_tag": tag,
                "build_result": build_result,
                "container_result": container_result,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _deploy_kubernetes(self, project_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Kubernetes."""
        try:
            # Get Cloud provider for Kubernetes manifests
            cloud_provider = provider_registry.get_provider("cloud")

            # Generate Kubernetes manifests
            k8s_config = {
                "package_name": Path(project_path).name,
                "replicas": config.get("replicas", 3),
            }

            manifests = cloud_provider.generate_kubernetes_manifests(k8s_config)

            # Write manifests to project directory
            project_dir = Path(project_path)
            k8s_dir = project_dir / "k8s"
            k8s_dir.mkdir(exist_ok=True)

            for filename, content in manifests.items():
                manifest_file = k8s_dir / filename
                manifest_file.write_text(content)

            return {
                "success": True,
                "deployment_type": "kubernetes",
                "manifests_generated": list(manifests.keys()),
                "manifests_dir": str(k8s_dir),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _deploy_cloud(self, project_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to cloud platform."""
        try:
            # Get Cloud provider
            cloud_provider = provider_registry.get_provider("cloud")

            # Generate Terraform configuration
            terraform_config = {
                "package_name": Path(project_path).name,
                "cloud_provider": config.get("provider", "aws"),
            }

            terraform_content = cloud_provider.generate_terraform_config(terraform_config)

            # Write Terraform files to project directory
            project_dir = Path(project_path)
            terraform_dir = project_dir / "terraform"
            terraform_dir.mkdir(exist_ok=True)

            terraform_file = terraform_dir / "main.tf"
            terraform_file.write_text(terraform_content)

            return {
                "success": True,
                "deployment_type": "cloud",
                "cloud_provider": config.get("provider", "aws"),
                "terraform_dir": str(terraform_dir),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """Check if deployment stage can execute."""
        # Need project path from generation stage
        generation_result = context.get("generation_result", {})
        project_path = generation_result.get("project_path")

        return project_path is not None
