"""
Comprehensive monitoring and metrics endpoints for OpenPypi API.
"""

import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException, Request
from openai import OpenAI
from pydantic import BaseModel

from openpypi.api.dependencies import get_config, get_openai_client
from openpypi.core.config import Config
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class SystemMetrics(BaseModel):
    """System resource metrics."""

    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: Optional[List[float]] = None
    network_io: Optional[Dict[str, int]] = None


class ApplicationMetrics(BaseModel):
    """Application-specific metrics."""

    uptime_seconds: float
    requests_total: int
    requests_per_second: float
    errors_total: int
    error_rate: float
    response_time_avg: float
    response_time_p95: float
    response_time_p99: float
    active_requests: int


class HealthStatus(BaseModel):
    """Overall health status."""

    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    uptime_seconds: float
    version: str
    environment: str


class ServiceStatus(BaseModel):
    """Individual service status."""

    name: str
    status: str  # healthy, unhealthy, not_configured
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_check: datetime


class MonitoringResponse(BaseModel):
    """Complete monitoring response."""

    health: HealthStatus
    system: SystemMetrics
    application: ApplicationMetrics
    services: List[ServiceStatus]


def get_system_metrics() -> SystemMetrics:
    """Get current system resource metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)

        # Disk metrics
        disk = psutil.disk_usage("/")
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)

        # Load average (Unix-like systems only)
        load_average = None
        try:
            if hasattr(psutil, "getloadavg"):
                load_average = list(psutil.getloadavg())
        except (AttributeError, OSError):
            pass

        # Network I/O
        network_io = None
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                network_io = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                }
        except Exception:
            pass

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_gb=round(memory_available_gb, 2),
            disk_usage_percent=round(disk_usage_percent, 2),
            disk_free_gb=round(disk_free_gb, 2),
            load_average=load_average,
            network_io=network_io,
        )

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        # Return default values if metrics collection fails
        return SystemMetrics(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_available_gb=0.0,
            disk_usage_percent=0.0,
            disk_free_gb=0.0,
        )


def get_application_metrics(request: Request) -> ApplicationMetrics:
    """Get application-specific metrics."""
    try:
        # Get uptime
        uptime_seconds = 0.0
        if hasattr(request.app.state, "startup_time"):
            uptime_seconds = time.time() - request.app.state.startup_time

        # Get metrics from middleware if available
        metrics = {}
        for middleware in request.app.user_middleware:
            if hasattr(middleware.cls, "metrics"):
                metrics = middleware.cls.metrics
                break

        # Calculate derived metrics
        requests_total = metrics.get("requests_total", 0)
        errors_total = metrics.get("errors_total", 0)
        error_rate = (errors_total / requests_total * 100) if requests_total > 0 else 0.0
        requests_per_second = requests_total / uptime_seconds if uptime_seconds > 0 else 0.0

        # Response time metrics
        response_times = metrics.get("response_times", [])
        response_time_avg = statistics.mean(response_times) if response_times else 0.0
        response_time_p95 = (
            statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0.0
        )
        response_time_p99 = (
            statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0.0
        )

        active_requests = metrics.get("active_requests", 0)

        return ApplicationMetrics(
            uptime_seconds=round(uptime_seconds, 2),
            requests_total=requests_total,
            requests_per_second=round(requests_per_second, 2),
            errors_total=errors_total,
            error_rate=round(error_rate, 2),
            response_time_avg=round(response_time_avg * 1000, 2),  # Convert to ms
            response_time_p95=round(response_time_p95 * 1000, 2),
            response_time_p99=round(response_time_p99 * 1000, 2),
            active_requests=active_requests,
        )

    except Exception as e:
        logger.error(f"Failed to get application metrics: {e}")
        return ApplicationMetrics(
            uptime_seconds=0.0,
            requests_total=0,
            requests_per_second=0.0,
            errors_total=0,
            error_rate=0.0,
            response_time_avg=0.0,
            response_time_p95=0.0,
            response_time_p99=0.0,
            active_requests=0,
        )


async def check_service_health(service_name: str, check_function, *args, **kwargs) -> ServiceStatus:
    """Check the health of a specific service."""
    start_time = time.time()

    try:
        await check_function(*args, **kwargs) if check_function else None
        response_time_ms = (time.time() - start_time) * 1000

        return ServiceStatus(
            name=service_name,
            status="healthy",
            response_time_ms=round(response_time_ms, 2),
            last_check=datetime.now(timezone.utc),
        )

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000

        return ServiceStatus(
            name=service_name,
            status="unhealthy",
            response_time_ms=round(response_time_ms, 2),
            error_message=str(e),
            last_check=datetime.now(timezone.utc),
        )


async def check_openai_service(openai_client: OpenAI) -> None:
    """Check OpenAI service health."""
    if not openai_client:
        raise Exception("OpenAI client not configured")

    # Make a lightweight API call
    models = openai_client.models.list(limit=1)
    if not models or not models.data:
        raise Exception("No models available")


async def check_filesystem_service() -> None:
    """Check filesystem health."""
    # Test file system write access
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(b"health check")
        tmp.flush()
        os.fsync(tmp.fileno())


@router.get("/metrics", response_model=MonitoringResponse)
async def get_comprehensive_metrics(
    request: Request,
    config: Config = Depends(get_config),
    openai_client: OpenAI = Depends(get_openai_client),
) -> MonitoringResponse:
    """Get comprehensive system and application metrics."""

    # Get basic metrics
    system_metrics = get_system_metrics()
    app_metrics = get_application_metrics(request)

    # Check service health
    services = []

    # Check OpenAI service
    if openai_client:
        openai_status = await check_service_health("openai", check_openai_service, openai_client)
    else:
        openai_status = ServiceStatus(
            name="openai", status="not_configured", last_check=datetime.now(timezone.utc)
        )
    services.append(openai_status)

    # Check filesystem
    fs_status = await check_service_health("filesystem", check_filesystem_service)
    services.append(fs_status)

    # Determine overall health status
    service_statuses = [s.status for s in services]
    if "unhealthy" in service_statuses:
        overall_status = "unhealthy"
    elif "degraded" in service_statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Create health status
    health_status = HealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=app_metrics.uptime_seconds,
        version="0.1.0",  # Get from config or package
        environment=getattr(config, "environment", "development"),
    )

    return MonitoringResponse(
        health=health_status, system=system_metrics, application=app_metrics, services=services
    )


@router.get("/health/live")
async def liveness_probe() -> Dict[str, Any]:
    """Kubernetes liveness probe - checks if the application is running."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": psutil.Process().pid,
    }


@router.get("/health/ready")
async def readiness_probe(
    request: Request, openai_client: OpenAI = Depends(get_openai_client)
) -> Dict[str, Any]:
    """Kubernetes readiness probe - checks if the application is ready to serve traffic."""

    ready = True
    checks = {}

    # Check if app is initialized
    if not hasattr(request.app.state, "startup_time"):
        ready = False
        checks["app_initialized"] = False
    else:
        checks["app_initialized"] = True

        # Check minimum startup time
        uptime = time.time() - request.app.state.startup_time
        if uptime < 2:  # Allow 2 seconds for startup
            ready = False
            checks["startup_complete"] = False
        else:
            checks["startup_complete"] = True

    # Check critical dependencies
    try:
        if openai_client:
            openai_client.models.list(limit=1)
            checks["openai"] = True
        else:
            checks["openai"] = "not_configured"
    except Exception:
        # OpenAI not being available shouldn't make the app unready
        checks["openai"] = "degraded"

    return {
        "status": "ready" if ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@router.get("/metrics/system")
async def get_system_metrics_endpoint() -> SystemMetrics:
    """Get detailed system resource metrics."""
    return get_system_metrics()


@router.get("/metrics/application")
async def get_application_metrics_endpoint(request: Request) -> ApplicationMetrics:
    """Get detailed application metrics."""
    return get_application_metrics(request)


@router.get("/info")
async def get_application_info() -> Dict[str, Any]:
    """Get application information and environment details."""
    return {
        "name": "OpenPypi API",
        "version": "0.1.0",
        "description": "Complete Python Project Generator with AI Integration",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "architecture": platform.architecture()[0],
        "hostname": platform.node(),
        "pid": psutil.Process().pid,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "features": [
            "AI-powered project generation",
            "FastAPI web framework",
            "Docker containerization",
            "Comprehensive testing",
            "CI/CD pipeline generation",
            "Multi-cloud deployment",
            "Real-time monitoring",
            "Security middleware",
            "Rate limiting",
            "Request tracing",
        ],
    }
