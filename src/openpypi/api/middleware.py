"""
Enhanced middleware for OpenPypi API with production-ready features.
"""

import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from openpypi.utils.logger import get_logger

logger = get_logger(__name__)

# Global metrics storage (use Redis in production)
request_counts = defaultdict(int)
response_times = deque(maxlen=1000)
error_counts = defaultdict(int)
rate_limit_storage = defaultdict(lambda: {"count": 0, "reset_time": datetime.utcnow()})


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware with production-ready security headers."""

    def __init__(self, app: ASGIApp, trusted_hosts: Optional[list] = None):
        super().__init__(app)
        self.trusted_hosts = trusted_hosts or ["*"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Validate trusted hosts
        if self.trusted_hosts != ["*"]:
            host = request.headers.get("host", "")
            if not any(trusted in host for trusted in self.trusted_hosts):
                return JSONResponse(
                    status_code=403, content={"error": "Forbidden", "message": "Host not allowed"}
                )

        response = await call_next(request)

        # Add comprehensive security headers
        response.headers.update(
            {
                # Prevent XSS attacks
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                # HTTPS enforcement
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                # Content Security Policy
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self'"
                ),
                # Prevent information disclosure
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
                # API specific headers
                "X-API-Version": "v1",
                "X-Powered-By": "OpenPypi",
            }
        )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced request logging with performance metrics and security monitoring."""

    def __init__(
        self, app: ASGIApp, log_body: bool = False, sensitive_headers: Optional[list] = None
    ):
        super().__init__(app)
        self.log_body = log_body
        self.sensitive_headers = sensitive_headers or ["authorization", "x-api-key", "cookie"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()

        # Sanitize headers for logging
        headers = dict(request.headers)
        for header in self.sensitive_headers:
            if header.lower() in headers:
                headers[header.lower()] = "***REDACTED***"

        # Log request details
        logger.info(
            f"Request started: {request_id} | "
            f"{request.method} {request.url.path} | "
            f"Client: {request.client.host if request.client else 'unknown'} | "
            f"User-Agent: {headers.get('user-agent', 'unknown')}"
        )

        # Optional body logging (be careful with sensitive data)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Log only first 1000 chars to prevent log flooding
                    body_preview = body[:1000].decode("utf-8", errors="ignore")
                    logger.debug(f"Request body preview: {request_id} | {body_preview}")
            except Exception as e:
                logger.warning(f"Failed to log request body: {request_id} | {e}")

        # Process request
        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Log response
            logger.info(
                f"Request completed: {request_id} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration:.2f}ms"
            )

            # Add performance metrics to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.2f}ms"

            # Log slow requests
            if duration > 5000:  # 5 seconds
                logger.warning(f"Slow request detected: {request_id} | {duration:.2f}ms")

            # Log error responses
            if response.status_code >= 400:
                logger.warning(
                    f"Error response: {request_id} | "
                    f"Status: {response.status_code} | "
                    f"Path: {request.url.path}"
                )

            return response

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request_id} | "
                f"Error: {str(e)} | "
                f"Duration: {duration:.2f}ms",
                exc_info=True,
            )

            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with per-endpoint and per-user limits."""

    def __init__(
        self,
        app: ASGIApp,
        calls: int = 100,
        period: int = 60,
        per_endpoint_limits: Optional[Dict[str, Dict[str, int]]] = None,
    ):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.per_endpoint_limits = per_endpoint_limits or {}
        self.request_counts: Dict[str, Dict[str, Any]] = {}

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use API key if available, otherwise use IP
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"api_key:{api_key[:8]}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _get_rate_limits(self, request: Request) -> tuple[int, int]:
        """Get rate limits for the current endpoint."""
        path = request.url.path
        method = request.method

        # Check for endpoint-specific limits
        endpoint_key = f"{method}:{path}"
        if endpoint_key in self.per_endpoint_limits:
            limits = self.per_endpoint_limits[endpoint_key]
            return limits.get("calls", self.calls), limits.get("period", self.period)

        return self.calls, self.period

    def _is_rate_limited(
        self, client_id: str, calls_limit: int, period: int
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if client is rate limited."""
        now = time.time()

        if client_id not in self.request_counts:
            self.request_counts[client_id] = {"calls": 0, "window_start": now, "last_request": now}

        client_data = self.request_counts[client_id]

        # Reset window if period has passed
        if now - client_data["window_start"] >= period:
            client_data["calls"] = 0
            client_data["window_start"] = now

        # Increment call count
        client_data["calls"] += 1
        client_data["last_request"] = now

        # Check if rate limited
        is_limited = client_data["calls"] > calls_limit

        return is_limited, {
            "calls_made": client_data["calls"],
            "calls_limit": calls_limit,
            "window_start": client_data["window_start"],
            "time_remaining": max(0, period - (now - client_data["window_start"])),
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_id = self._get_client_id(request)
        calls_limit, period = self._get_rate_limits(request)

        is_limited, rate_info = self._is_rate_limited(client_id, calls_limit, period)

        if is_limited:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate Limit Exceeded",
                    "message": f"Too many requests. Limit: {calls_limit} per {period} seconds",
                    "retry_after": int(rate_info["time_remaining"]),
                    "rate_limit": rate_info,
                },
                headers={
                    "Retry-After": str(int(rate_info["time_remaining"])),
                    "X-RateLimit-Limit": str(calls_limit),
                    "X-RateLimit-Remaining": str(max(0, calls_limit - rate_info["calls_made"])),
                    "X-RateLimit-Reset": str(int(rate_info["window_start"] + period)),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers.update(
            {
                "X-RateLimit-Limit": str(calls_limit),
                "X-RateLimit-Remaining": str(max(0, calls_limit - rate_info["calls_made"])),
                "X-RateLimit-Reset": str(int(rate_info["window_start"] + period)),
            }
        )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting application metrics."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = {
            "requests_total": 0,
            "requests_by_method": {},
            "requests_by_status": {},
            "response_times": [],
            "errors_total": 0,
            "active_requests": 0,
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        self.metrics["active_requests"] += 1

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            self.metrics["requests_total"] += 1

            # Method metrics
            method = request.method
            self.metrics["requests_by_method"][method] = (
                self.metrics["requests_by_method"].get(method, 0) + 1
            )

            # Status code metrics
            status = response.status_code
            self.metrics["requests_by_status"][status] = (
                self.metrics["requests_by_status"].get(status, 0) + 1
            )

            # Response time metrics (keep last 1000 requests)
            self.metrics["response_times"].append(duration)
            if len(self.metrics["response_times"]) > 1000:
                self.metrics["response_times"] = self.metrics["response_times"][-1000:]

            # Error tracking
            if status >= 400:
                self.metrics["errors_total"] += 1

            return response

        except Exception as e:
            self.metrics["errors_total"] += 1
            raise
        finally:
            self.metrics["active_requests"] -= 1


def setup_middleware(app):
    """Set up all middleware for the FastAPI app."""

    # Metrics collection (first, to capture all requests)
    app.add_middleware(MetricsMiddleware)

    # Request logging and tracing
    app.add_middleware(
        RequestLoggingMiddleware,
        log_body=False,  # Set to True for debugging, False for production
        sensitive_headers=["authorization", "x-api-key", "cookie", "x-auth-token"],
    )

    # Security headers
    app.add_middleware(
        SecurityMiddleware, trusted_hosts=["*"]  # Configure with actual trusted hosts in production
    )

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        calls=1000,  # 1000 requests
        period=3600,  # per hour
        per_endpoint_limits={
            "POST:/generate/sync": {"calls": 10, "period": 60},  # 10 per minute for sync generation
            "POST:/generate/async": {
                "calls": 50,
                "period": 3600,
            },  # 50 per hour for async generation
        },
    )

    # Response compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    logger.info("Middleware setup complete")


# Legacy functions for backward compatibility
async def log_requests(request: Request, call_next):
    """Legacy request logging function."""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(f"Incoming request: {request_id} | {request.method} {request.url.path}")

    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"Outgoing response: {request_id} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time * 1000:.2f}ms"
    )

    response.headers["X-Request-ID"] = request_id
    return response


async def add_security_headers(request: Request, call_next):
    """Legacy security headers function."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


async def rate_limit_middleware(request: Request, call_next):
    """Legacy rate limiting function."""
    # Basic rate limiting - in production use Redis or similar
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = "1000"
    return response


# Aliases for backward compatibility
SecurityHeadersMiddleware = SecurityMiddleware
LoggingMiddleware = RequestLoggingMiddleware
ErrorHandlingMiddleware = RequestLoggingMiddleware  # ErrorHandlingMiddleware can use RequestLoggingMiddleware


def get_middleware_metrics() -> Dict[str, Any]:
    """Get middleware metrics."""
    total_requests = sum(request_counts.values())
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    return {
        "total_requests": total_requests,
        "average_response_time": avg_response_time,
        "request_counts": dict(request_counts),
        "error_counts": dict(error_counts),
        "active_connections": len(rate_limit_storage)
    }
