"""
Main FastAPI application for OpenPypi.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from openpypi.core.config import Config
from openpypi.utils.logger import get_logger

from .middleware import setup_middleware
from .routes import auth, generation, health, monitoring, projects

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting OpenPypi API...")

    # Initialize services
    app.state.config = Config()
    app.state.startup_time = time.time()

    # Health check for external services
    try:
        # Test OpenAI connection if configured
        if hasattr(app.state.config, "openai_api_key") and app.state.config.openai_api_key:
            from openai import OpenAI

            client = OpenAI(api_key=app.state.config.openai_api_key)
            # Simple test call
            try:
                client.models.list(limit=1)
                logger.info("OpenAI API connection successful")
            except Exception as e:
                logger.warning(f"OpenAI API connection failed: {e}")

        logger.info("OpenPypi API started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

    yield

    # Shutdown
    logger.info("Shutting down OpenPypi API...")


# Create FastAPI app
app = FastAPI(
    title="OpenPypi API",
    description="Complete Python Project Generator with AI Integration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Setup enhanced middleware
setup_middleware(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted hosts middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]  # Configure this properly for production
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-change-this-in-production",  # Change in production
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])

app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

app.include_router(generation.router, prefix="/generate", tags=["Project Generation"])

app.include_router(projects.router, prefix="/projects", tags=["Project Management"])


# Add root-level health endpoints for Kubernetes probes
@app.get("/ready", summary="Readiness Probe", tags=["Health"])
async def readiness_probe(request: Request) -> dict:
    """Kubernetes readiness probe endpoint."""
    try:
        # Check if app is properly initialized
        if not hasattr(request.app.state, "startup_time"):
            return {"status": "not_ready", "reason": "app not initialized"}

        # Check if minimum startup time has passed
        startup_time = request.app.state.startup_time
        if time.time() - startup_time < 5:  # Minimum 5 seconds startup time
            return {"status": "not_ready", "reason": "startup in progress"}

        return {"status": "ready", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return {"status": "not_ready", "reason": str(e)}


@app.get("/live", summary="Liveness Probe", tags=["Health"])
async def liveness_probe() -> dict:
    """Kubernetes liveness probe endpoint."""
    # Basic liveness check - if this endpoint responds, the app is alive
    return {"status": "alive", "timestamp": time.time()}


@app.get("/", summary="Root endpoint", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": "OpenPypi API",
        "description": "Complete Python Project Generator with AI Integration",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_check": "/health",
        "monitoring": "/monitoring",
        "features": [
            "AI-powered project generation",
            "FastAPI integration",
            "Docker containerization",
            "Comprehensive testing",
            "CI/CD pipeline generation",
            "Multi-cloud deployment",
            "Real-time monitoring and metrics",
            "Security middleware",
            "Rate limiting",
            "Request tracing",
        ],
        "endpoints": {
            "health": "/health",
            "monitoring": "/monitoring",
            "generate": "/generate",
            "projects": "/projects",
            "auth": "/auth",
        },
    }


@app.get("/info", summary="Application information")
async def get_app_info(request: Request) -> Dict[str, Any]:
    """Get application information and stats."""
    uptime = time.time() - request.app.state.startup_time

    return {
        "application": "OpenPypi API",
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 2),
        "status": "running",
        "python_version": "3.11+",
        "framework": "FastAPI",
        "features": [
            "OpenAI Integration",
            "Project Generation",
            "Docker Support",
            "CI/CD Pipeline",
            "Multi-cloud Deployment",
            "Monitoring & Metrics",
            "Security Middleware",
            "Rate Limiting",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("openpypi.api.app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
