"""
Docker provider for container management with enhanced security features.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import docker
    from docker.errors import APIError, DockerException
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    APIError = Exception
    DockerException = Exception
    DOCKER_AVAILABLE = False

# Try to import trivy, but handle gracefully if not available
try:
    import trivy
    TRIVY_AVAILABLE = True
except ImportError:
    trivy = None
    TRIVY_AVAILABLE = False

from .base import BaseProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DockerProvider(BaseProvider):
    """Docker provider with comprehensive security and lifecycle management."""

    @property
    def name(self) -> str:
        return "docker"

    def __init__(self, config: Optional[Dict] = None):
        self.client = None
        self.security_config = {
            "scan_on_build": True,
            "quarantine_vulnerabilities": True,
            "max_vulnerability_score": 7.0,
            "allowed_registries": ["docker.io", "gcr.io", "ghcr.io"],
        }
        super().__init__(config)

    def _configure(self) -> None:
        """Configure Docker provider."""
        if not DOCKER_AVAILABLE:
            logger.warning("Docker package not available. Install with: pip install docker")
            self.is_configured = False
            return

        try:
            socket_url = self.config.get("socket_url", "unix:///var/run/docker.sock")
            timeout = self.config.get("timeout", 30)

            # Check if Docker daemon is accessible
            if socket_url.startswith("unix://") and not os.path.exists(socket_url[7:]):
                logger.warning(f"Docker socket not found: {socket_url}")
                self.is_configured = False
                return

            self.client = docker.DockerClient(base_url=socket_url, timeout=timeout)
            
            # Update security config
            if "security" in self.config:
                self.security_config.update(self.config["security"])
            
            self.is_configured = True
            logger.info("Docker provider configured successfully")

        except Exception as e:
            logger.error(f"Docker provider configuration failed: {e}")
            self.is_configured = False

    def validate_connection(self) -> bool:
        """Validate Docker daemon connection."""
        if not self.is_configured or not self.client:
            return False

        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Docker connection validation failed: {e}")
            return False

    def get_capabilities(self) -> List[str]:
        """Return Docker provider capabilities."""
        capabilities = [
            "build_image",
            "run_container",
            "manage_containers",
            "image_management",
            "network_management",
            "volume_management",
        ]
        
        if TRIVY_AVAILABLE or shutil.which("trivy"):
            capabilities.append("security_scanning")
        
        return capabilities

    def build_image(
        self,
        dockerfile_path: str,
        tag: str,
        context_path: str = ".",
        build_args: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build Docker image with security scanning."""
        if not self.is_configured:
            raise RuntimeError("Docker provider not configured")

        try:
            logger.info(f"Building Docker image: {tag}")
            
            # Build the image
            image, logs = self.client.images.build(
                path=context_path,
                dockerfile=dockerfile_path,
                tag=tag,
                buildargs=build_args or {},
                rm=True,
                **kwargs
            )

            result = {
                "image_id": image.id,
                "tags": image.tags,
                "size": image.attrs.get("Size", 0),
                "created": image.attrs.get("Created"),
                "success": True,
                "logs": [log.get("stream", "").strip() for log in logs if log.get("stream")],
            }

            # Security scanning if enabled
            if self.security_config.get("scan_on_build", True):
                scan_result = self.security_scan_image(tag)
                result["security_scan"] = scan_result
                
                # Quarantine if vulnerabilities found
                if (scan_result.get("vulnerabilities_found", False) and 
                    self.security_config.get("quarantine_vulnerabilities", True)):
                    self._quarantine_image(image, scan_result)
                    result["quarantined"] = True

            return result

        except Exception as e:
            logger.error(f"Docker image build failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_id": None,
                "tags": [],
            }

    def security_scan_image(self, image_tag: str) -> Dict[str, Any]:
        """Perform security scan on Docker image."""
        if not self.is_configured:
            raise RuntimeError("Docker provider not configured")

        scan_result = {
            "image": image_tag,
            "vulnerabilities_found": False,
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "low_severity_count": 0,
            "scan_method": None,
            "details": []
        }

        # Try using trivy command line if available
        if shutil.which("trivy"):
            try:
                cmd = [
                    "trivy", "image", 
                    "--format", "json", 
                    "--severity", "HIGH,CRITICAL,MEDIUM",
                    image_tag
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=300
                )
                
                if result.returncode == 0:
                    trivy_data = json.loads(result.stdout)
                    scan_result = self._parse_trivy_results(trivy_data, image_tag)
                    scan_result["scan_method"] = "trivy-cli"
                    return scan_result
                    
            except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Trivy CLI scan failed: {e}")

        # Try using trivy Python package if available
        elif TRIVY_AVAILABLE:
            try:
                # Use trivy Python API
                trivy_client = trivy.Trivy()
                results = trivy_client.scan_image(image_tag)
                scan_result = self._parse_trivy_results(results, image_tag)
                scan_result["scan_method"] = "trivy-python"
                return scan_result
                
            except Exception as e:
                logger.warning(f"Trivy Python scan failed: {e}")

        # Fallback: Basic image inspection
        try:
            image = self.client.images.get(image_tag)
            scan_result.update({
                "scan_method": "basic-inspection",
                "image_size": image.attrs.get("Size", 0),
                "architecture": image.attrs.get("Architecture"),
                "os": image.attrs.get("Os"),
                "created": image.attrs.get("Created"),
                "warning": "Full vulnerability scan not available - install trivy for comprehensive scanning"
            })
            
        except Exception as e:
            logger.error(f"Basic image inspection failed: {e}")
            scan_result["error"] = str(e)

        return scan_result

    def _parse_trivy_results(self, trivy_data: Dict, image_tag: str) -> Dict[str, Any]:
        """Parse trivy scan results into standardized format."""
        scan_result = {
            "image": image_tag,
            "vulnerabilities_found": False,
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "low_severity_count": 0,
            "details": []
        }

        # Handle different trivy output formats
        results = trivy_data.get("Results", [])
        if not results:
            return scan_result

        for result in results:
            vulnerabilities = result.get("Vulnerabilities", [])
            if not vulnerabilities:
                continue
                
            scan_result["vulnerabilities_found"] = True
            
            for vuln in vulnerabilities:
                severity = vuln.get("Severity", "UNKNOWN").upper()
                
                if severity in ["HIGH", "CRITICAL"]:
                    scan_result["high_severity_count"] += 1
                elif severity == "MEDIUM":
                    scan_result["medium_severity_count"] += 1
                else:
                    scan_result["low_severity_count"] += 1
                
                scan_result["details"].append({
                    "vulnerability_id": vuln.get("VulnerabilityID"),
                    "package": vuln.get("PkgName"),
                    "severity": severity,
                    "title": vuln.get("Title", ""),
                    "description": vuln.get("Description", "")[:200]  # Truncate
                })

        return scan_result

    def _quarantine_image(self, image, scan_result: Dict[str, Any]) -> None:
        """Quarantine image with security vulnerabilities."""
        try:
            # Tag image for quarantine
            quarantine_tag = f"quarantine/{image.tags[0] if image.tags else image.id[:12]}"
            image.tag(quarantine_tag)
            
            # Remove original tags
            for tag in image.tags[:]:  # Create copy to avoid modification during iteration
                if not tag.startswith("quarantine/"):
                    try:
                        self.client.images.remove(tag)
                    except Exception as e:
                        logger.warning(f"Failed to remove tag {tag}: {e}")
            
            logger.warning(f"Image quarantined due to security vulnerabilities: {quarantine_tag}")
            
        except Exception as e:
            logger.error(f"Image quarantine failed: {e}")

    def run_container(
        self,
        image: str,
        command: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        detach: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Run container with security constraints."""
        if not self.is_configured:
            raise RuntimeError("Docker provider not configured")

        try:
            # Security constraints
            security_opts = [
                "no-new-privileges:true",
                "apparmor=docker-default"
            ]
            
            container = self.client.containers.run(
                image=image,
                command=command,
                environment=environment or {},
                ports=ports or {},
                volumes=volumes or {},
                detach=detach,
                security_opt=security_opts,
                read_only=True,  # Make filesystem read-only by default
                **kwargs
            )

            return {
                "container_id": container.id,
                "name": container.name,
                "status": container.status,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Container run failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "container_id": None,
            }

    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List Docker containers."""
        if not self.is_configured:
            raise RuntimeError("Docker provider not configured")

        try:
            containers = self.client.containers.list(all=all_containers)
            return [
                {
                    "id": container.id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.id,
                    "status": container.status,
                    "created": container.attrs.get("Created"),
                }
                for container in containers
            ]
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def list_images(self) -> List[Dict[str, Any]]:
        """List Docker images."""
        if not self.is_configured:
            raise RuntimeError("Docker provider not configured")

        try:
            images = self.client.images.list()
            return [
                {
                    "id": image.id,
                    "tags": image.tags,
                    "size": image.attrs.get("Size", 0),
                    "created": image.attrs.get("Created"),
                }
                for image in images
            ]
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []

    def cleanup_resources(self, remove_unused: bool = True) -> Dict[str, Any]:
        """Clean up Docker resources."""
        if not self.is_configured:
            raise RuntimeError("Docker provider not configured")

        cleanup_result = {
            "containers_removed": 0,
            "images_removed": 0,
            "volumes_removed": 0,
            "networks_removed": 0,
            "space_reclaimed": 0,
        }

        try:
            if remove_unused:
                # Remove unused containers, images, volumes, and networks
                pruned = self.client.containers.prune()
                cleanup_result["containers_removed"] = len(pruned.get("ContainersDeleted", []))
                
                pruned = self.client.images.prune()
                cleanup_result["images_removed"] = len(pruned.get("ImagesDeleted", []))
                cleanup_result["space_reclaimed"] = pruned.get("SpaceReclaimed", 0)
                
                pruned = self.client.volumes.prune()
                cleanup_result["volumes_removed"] = len(pruned.get("VolumesDeleted", []))
                
                pruned = self.client.networks.prune()
                cleanup_result["networks_removed"] = len(pruned.get("NetworksDeleted", []))

            return cleanup_result

        except Exception as e:
            logger.error(f"Docker cleanup failed: {e}")
            cleanup_result["error"] = str(e)
            return cleanup_result

    def shutdown(self):
        """Shutdown Docker provider and cleanup resources."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.warning(f"Error closing Docker client: {e}")
        
        super().shutdown()
