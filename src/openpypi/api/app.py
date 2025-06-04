"""
OpenPypi FastAPI Application
Production-ready API with comprehensive security, monitoring, and error handling
"""

import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from openpypi.core.config import get_settings, load_config
from openpypi.core.exceptions import OpenPypiException
from openpypi.database.session import engine, get_db
from openpypi.api.middleware import (
    SecurityMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    MetricsMiddleware,
)
from openpypi.api.routes import (
    auth_router,
    projects_router,
    packages_router,
    health_router,
    admin_router,
    generation_router,
    monitoring_router,
    openai_router,
)
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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    settings = get_settings()
    
    # Startup
    logger.info("Starting OpenPypi API server", version=app.version)
    
    # Initialize database
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        if settings.app_env == "production":
            raise
    
    # Initialize monitoring
    if settings.app_env == "production":
        instrumentator = Instrumentator()
        instrumentator.instrument(app).expose(app)
        logger.info("Prometheus metrics enabled")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpenPypi API server")
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="OpenPypi API",
        description="AI-powered Python package creation, testing, and publishing platform",
        version="0.3.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Security middleware (order matters!)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"]
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(TimingMiddleware)
    
    # Include routers
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(packages_router, prefix="/api/v1/packages", tags=["packages"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(generation_router, prefix="/api/v1/generate", tags=["generation"])
    app.include_router(monitoring_router, prefix="/api/v1/monitoring", tags=["monitoring"])
    app.include_router(openai_router, prefix="/api/v1/openai", tags=["openai"])
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            }
        }
        
        # Add global security
        openapi_schema["security"] = [
            {"BearerAuth": []},
            {"ApiKeyAuth": []}
        ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # Custom docs endpoints
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        )
    
    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": "OpenPypi API",
            "version": "0.3.0",
            "description": "AI-powered Python package creation platform",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health"
        }
    
    # Global exception handlers
    @app.exception_handler(OpenPypiException)
    async def openpypi_exception_handler(request: Request, exc: OpenPypiException):
        logger.error(
            "OpenPypi exception occurred",
            error=str(exc),
            error_code=exc.error_code,
            path=request.url.path,
            method=request.method
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": str(exc),
                "detail": exc.detail,
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning(
            "Value error occurred",
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_error",
                "message": str(exc),
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unexpected error occurred",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
            exc_info=True
        )
        
        if settings.app_env == "development":
            import traceback
            detail = traceback.format_exc()
        else:
            detail = "An unexpected error occurred"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "detail": detail if settings.app_env == "development" else None,
                "timestamp": time.time()
            }
        )
    
    return app


# Create the application instance
app = create_app()


def main():
    """Main entry point for running the server."""
    settings = get_settings()
    
    # Configure logging
    log_level = settings.log_level.upper()
    logging.basicConfig(level=getattr(logging, log_level))
    
    # Run server
    uvicorn.run(
        "openpypi.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload and settings.app_env == "development",
        workers=1,  # Use 1 worker for development, Gunicorn handles workers in production
        log_level=log_level.lower(),
        access_log=True,
        use_colors=True,
    )


if __name__ == "__main__":
    main()
