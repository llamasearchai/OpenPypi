"""
API routes for health checks.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from openai import OpenAI

from openpypi._version import __version__
from openpypi.api.dependencies import get_db, get_openai_client
from openpypi.api.schemas import APIResponse, HealthStatus
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "",
    response_model=HealthStatus,
    summary="Get API Health Status",
    description="Provides the current operational status of the API and its dependencies.",
)
async def get_health(
    request: Request,
    # db: Session = Depends(get_db), # Example: Add DB dependency if needed for health check
    openai_client: OpenAI = Depends(get_openai_client),
) -> HealthStatus:
    """Return the health status of the API."""
    logger.info("Health check endpoint called")

    dependencies_status = {}
    overall_status = "healthy"

    # Check Database Health (Placeholder)
    try:
        # Perform a simple query or check connection
        # For now, assuming DB is healthy if dependency resolves
        # if db is not None: # Or some specific check like db.is_connected()
        #    dependencies_status["database"] = "healthy"
        # else:
        #    dependencies_status["database"] = "degraded"
        #    overall_status = "degraded"
        dependencies_status["database"] = "not_checked"  # Placeholder
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        dependencies_status["database"] = "unhealthy"
        overall_status = "unhealthy"

    # Check OpenAI API Health
    if openai_client:
        try:
            openai_client.models.list(limit=1)  # lightweight call
            dependencies_status["openai_api"] = "healthy"
        except Exception as e:
            logger.warning(f"OpenAI API health check failed: {e}")
            dependencies_status["openai_api"] = "unhealthy"
            # Potentially degrade overall status, depending on criticality
            # overall_status = "degraded" if overall_status == "healthy" else overall_status
    else:
        dependencies_status["openai_api"] = "not_configured"

    uptime_seconds = None
    if hasattr(request.app.state, "startup_time") and request.app.state.startup_time:
        uptime_seconds = round(time.time() - request.app.state.startup_time, 2)

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        dependencies=dependencies_status,
        uptime_seconds=uptime_seconds,
        version=__version__,
    )


@router.get(
    "/detailed",
    response_model=HealthStatus,
    summary="Get Detailed Health Status",
    description="Provides detailed health status with more comprehensive checks.",
)
async def get_detailed_health(
    request: Request, openai_client: OpenAI = Depends(get_openai_client)
) -> HealthStatus:
    """Return detailed health status with comprehensive checks."""
    logger.info("Detailed health check endpoint called")

    dependencies_status = {}
    overall_status = "healthy"

    # More comprehensive checks for detailed health
    dependencies_status["api"] = "healthy"
    dependencies_status["database"] = "not_configured"  # Placeholder

    # Check OpenAI API with more detail
    if openai_client:
        try:
            models = openai_client.models.list(limit=1)
            if models and models.data:
                dependencies_status["openai_api"] = "healthy"
            else:
                dependencies_status["openai_api"] = "degraded"
                overall_status = "degraded"
        except Exception as e:
            logger.warning(f"OpenAI API detailed check failed: {e}")
            dependencies_status["openai_api"] = "unhealthy"
            overall_status = "degraded"
    else:
        dependencies_status["openai_api"] = "not_configured"

    # File system checks
    try:
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp.write(b"health check")
            tmp.flush()
            os.fsync(tmp.fileno())
        dependencies_status["filesystem"] = "healthy"
    except Exception as e:
        logger.error(f"Filesystem health check failed: {e}")
        dependencies_status["filesystem"] = "unhealthy"
        overall_status = "unhealthy"

    uptime_seconds = None
    if hasattr(request.app.state, "startup_time") and request.app.state.startup_time:
        uptime_seconds = round(time.time() - request.app.state.startup_time, 2)

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        dependencies=dependencies_status,
        uptime_seconds=uptime_seconds,
        version=__version__,
    )


@router.get("/ping", response_model=APIResponse, summary="Simple Ping Endpoint")
async def ping() -> APIResponse:
    """A simple ping endpoint to check if the API is responsive."""
    return APIResponse(success=True, message="pong")


@router.get("/ready", response_model=APIResponse, summary="Kubernetes Readiness Probe")
async def readiness_probe() -> APIResponse:
    """Kubernetes readiness probe endpoint."""
    return APIResponse(success=True, message="ready")


@router.get("/live", response_model=APIResponse, summary="Kubernetes Liveness Probe")
async def liveness_probe() -> APIResponse:
    """Kubernetes liveness probe endpoint."""
    return APIResponse(success=True, message="alive")
