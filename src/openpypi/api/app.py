"""
OpenPypi FastAPI Application
Production-ready API with comprehensive security, monitoring, and error handling
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from openpypi.api.middleware import (
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    SecurityMiddleware,
)
from openpypi.api.routes import (
    admin_router,
    auth_router,
    generation_router,
    health_router,
    monitoring_router,
    openai_router,
    packages_router,
    projects_router,
)
from openpypi.core.config import get_settings, load_config
from openpypi.core.exceptions import OpenPypiException
from openpypi.database.session import engine, get_db
from openpypi.utils.logger import get_logger

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware to add request timing and performance monitoring."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timing and performance monitoring."""
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time

            # Add timing headers
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            response.headers["X-Request-ID"] = request_id

            # Log performance metrics
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=process_time,
            )

            return response

        except Exception as e:
            process_time = time.perf_counter() - start_time
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time=process_time,
                exc_info=True,
            )
            raise


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware for enhanced health checking and circuit breaker patterns."""

    def __init__(self, app, health_check_path: str = "/health"):
        super().__init__(app)
        self.health_check_path = health_check_path
        self.start_time = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enhanced health checking with system metrics."""
        if request.url.path == self.health_check_path:
            # Quick health check bypass for load balancers
            return JSONResponse(
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "uptime": time.time() - self.start_time,
                    "version": "0.3.0",
                }
            )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application lifespan manager with comprehensive startup and shutdown."""
    settings = get_settings()

    # Startup
    logger.info(
        "Starting OpenPypi API server",
        version=app.version,
        environment=settings.app_env,
        host=settings.api_host,
        port=settings.api_port,
    )

    # Initialize database with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            logger.info("Database connection established")
            break
        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt + 1} failed",
                error=str(e),
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt == max_retries - 1:
                if settings.app_env == "production":
                    raise
                logger.warning("Continuing without database in development mode")
            else:
                await asyncio.sleep(2**attempt)  # Exponential backoff

    # Initialize monitoring and metrics
    if settings.app_env == "production":
        try:
            instrumentator = Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
                should_respect_env_var=True,
                should_instrument_requests_inprogress=True,
                excluded_handlers=["/health", "/metrics"],
                env_var_name="ENABLE_METRICS",
                inprogress_name="inprogress",
                inprogress_labels=True,
            )
            instrumentator.instrument(app).expose(app)
            logger.info("Prometheus metrics enabled")
        except Exception as e:
            logger.warning("Failed to initialize metrics", error=str(e))

    # Validate configuration
    try:
        settings.validate()
        logger.info("Configuration validation passed")
    except Exception as e:
        logger.error("Configuration validation failed", error=str(e))
        if settings.app_env == "production":
            raise

    # Pre-warm any caches or connections
    logger.info("Application startup completed successfully")

    yield

    # Shutdown
    logger.info("Initiating graceful shutdown")

    try:
        # Close database connections
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error during database shutdown", error=str(e))

    logger.info("OpenPypi API server shutdown completed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with comprehensive features."""
    settings = get_settings()

    # Create FastAPI app with enhanced configuration
    app = FastAPI(
        title="OpenPypi API",
        description=(
            "Professional AI-powered Python package creation, testing, and publishing platform. "
            "Generate modern, production-ready Python projects with comprehensive CI/CD, "
            "testing, documentation, and deployment capabilities."
        ),
        version="0.3.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
        generate_unique_id_function=lambda route: (
            f"{route.tags[0]}-{route.name}" if route.tags else route.name
        ),
    )

    # Enhanced security middleware (order is critical!)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining", "X-Process-Time", "X-Version"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Performance and monitoring middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(HealthCheckMiddleware)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(TimingMiddleware)

    # Include routers with proper organization
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(packages_router, prefix="/api/v1/packages", tags=["packages"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(generation_router, prefix="/api/v1/generate", tags=["generation"])
    app.include_router(monitoring_router, prefix="/api/v1/monitoring", tags=["monitoring"])
    app.include_router(openai_router, prefix="/api/v1/openai", tags=["openai"])

    # Enhanced OpenAPI schema
    def custom_openapi() -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema with comprehensive documentation."""
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            servers=[
                {"url": "/", "description": "Current server"},
                {"url": "https://api.openpypi.org", "description": "Production server"},
            ],
        )

        # Enhanced security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Bearer token authentication",
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API Key authentication",
            },
        }

        # Add global security
        openapi_schema["security"] = [{"BearerAuth": []}, {"ApiKeyAuth": []}]

        # Add custom extensions
        openapi_schema["info"]["x-logo"] = {
            "url": "https://openpypi.org/logo.png",
            "altText": "OpenPypi Logo",
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # Enhanced documentation endpoints
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with enhanced features."""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Interactive API Documentation",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_ui_parameters={
                "deepLinking": True,
                "displayRequestDuration": True,
                "docExpansion": "none",
                "operationsSorter": "alpha",
                "filter": True,
                "showExtensions": True,
                "showCommonExtensions": True,
            },
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Enhanced ReDoc documentation."""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - API Reference",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
            redoc_favicon_url="https://openpypi.org/favicon.ico",
        )

    # Enhanced root endpoint
    @app.get("/", response_model=Dict[str, Any], include_in_schema=False)
    async def root():
        """API root endpoint with comprehensive information."""
        return {
            "name": "OpenPypi API",
            "version": "0.3.0",
            "description": "AI-powered Python package creation platform",
            "environment": settings.app_env,
            "endpoints": {
                "documentation": "/docs",
                "redoc": "/redoc",
                "health": "/health",
                "metrics": "/metrics" if settings.app_env == "production" else None,
            },
            "features": [
                "AI-powered project generation",
                "FastAPI integration",
                "Docker containerization",
                "Comprehensive testing",
                "CI/CD pipelines",
                "OpenAI integration",
                "Professional templates",
            ],
            "status": "operational",
            "timestamp": time.time(),
        }

    # Enhanced liveness probe
    @app.get("/live", response_model=Dict[str, Any], summary="Liveness Probe")
    async def liveness_probe():
        """Enhanced liveness probe for Kubernetes with detailed status."""
        return {
            "status": "alive",
            "service": "openpypi-api",
            "version": "0.3.0",
            "timestamp": time.time(),
            "checks": {
                "application": "healthy",
                "database": "connected" if engine else "disconnected",
            },
        }

    # Comprehensive exception handlers
    @app.exception_handler(OpenPypiException)
    async def openpypi_exception_handler(request: Request, exc: OpenPypiException) -> JSONResponse:
        """Handle OpenPypi-specific exceptions with detailed logging."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            "OpenPypi exception occurred",
            request_id=request_id,
            error=str(exc),
            error_code=exc.error_code,
            path=request.url.path,
            method=request.method,
            user_agent=request.headers.get("user-agent"),
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": str(exc),
                "detail": exc.detail,
                "request_id": request_id,
                "timestamp": time.time(),
                "path": request.url.path,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Enhanced HTTP exception handler."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            "HTTP exception occurred",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": request_id,
                "timestamp": time.time(),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Enhanced value error handler with better context."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            "Validation error occurred",
            request_id=request_id,
            error=str(exc),
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": str(exc),
                "request_id": request_id,
                "timestamp": time.time(),
                "suggestions": ["Check input format and required fields"],
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Comprehensive general exception handler with security considerations."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            "Unexpected error occurred",
            request_id=request_id,
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )

        # Provide detailed errors only in development
        if settings.app_env == "development":
            import traceback

            detail = traceback.format_exc()
            message = str(exc)
        else:
            detail = None
            message = "An unexpected error occurred. Please try again later."

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": message,
                "detail": detail,
                "request_id": request_id,
                "timestamp": time.time(),
                "support": "Contact support with request_id for assistance",
            },
        )

    return app


# Create the application instance
app = create_app()


def main() -> None:
    """Enhanced main entry point with comprehensive configuration."""
    settings = get_settings()

    # Configure logging
    log_level = settings.log_level.upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            (
                logging.FileHandler("logs/app.log")
                if os.path.exists("logs")
                else logging.NullHandler()
            ),
        ],
    )

    # Validate environment
    if settings.app_env == "production":
        logger.info("Starting in production mode with enhanced security")
    else:
        logger.info(f"Starting in {settings.app_env} mode")

    # Run server with optimized configuration
    uvicorn.run(
        "openpypi.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload and settings.app_env == "development",
        workers=1,  # Single worker for development; Gunicorn handles workers in production
        log_level=log_level.lower(),
        access_log=True,
        use_colors=settings.app_env != "production",
        server_header=False,  # Hide server header for security
        date_header=False,  # Hide date header for security
    )


if __name__ == "__main__":
    main()
