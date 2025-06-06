"""Monitoring utilities for OpenPypi."""

import time
from datetime import datetime
from typing import Any, Dict

import psutil

from .logger import get_logger

logger = get_logger(__name__)


def get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk metrics
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()

        # Network metrics
        network_io = psutil.net_io_counters()

        return {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "cpu_frequency": {
                "current": cpu_freq.current if cpu_freq else None,
                "min": cpu_freq.min if cpu_freq else None,
                "max": cpu_freq.max if cpu_freq else None,
            },
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "swap_percent": swap.percent,
            "swap_used": swap.used,
            "swap_total": swap.total,
            "disk_usage": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            },
            "disk_io": {
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0,
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0,
            },
            "network_io": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


def get_application_metrics() -> Dict[str, Any]:
    """Get application-specific metrics."""
    try:
        from ..api.middleware import get_middleware_metrics

        # Get middleware metrics
        middleware_metrics = get_middleware_metrics()

        # Add application-specific metrics
        return {
            "requests_total": middleware_metrics.get("total_requests", 0),
            "requests_per_second": calculate_requests_per_second(),
            "average_response_time": middleware_metrics.get("average_response_time", 0),
            "error_rate": calculate_error_rate(middleware_metrics),
            "active_connections": middleware_metrics.get("active_connections", 0),
            "uptime_seconds": get_uptime(),
            "version": "0.3.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting application metrics: {e}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


# Application start time for uptime calculation
_start_time = time.time()


def get_uptime() -> float:
    """Get application uptime in seconds."""
    return time.time() - _start_time


def calculate_requests_per_second() -> float:
    """Calculate requests per second."""
    try:
        from ..api.middleware import request_counts

        total_requests = sum(request_counts.values())
        uptime = get_uptime()
        return total_requests / uptime if uptime > 0 else 0
    except Exception:
        return 0.0


def calculate_error_rate(middleware_metrics: Dict[str, Any]) -> float:
    """Calculate error rate percentage."""
    try:
        total_requests = middleware_metrics.get("total_requests", 0)
        error_counts = middleware_metrics.get("error_counts", {})
        total_errors = sum(error_counts.values())

        if total_requests == 0:
            return 0.0

        return (total_errors / total_requests) * 100
    except Exception:
        return 0.0


class HealthChecker:
    """Health check manager."""

    def __init__(self):
        self.checks = {}

    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func

    async def run_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        overall_status = "healthy"

        for name, check_func in self.checks.items():
            try:
                if callable(check_func):
                    result = (
                        await check_func() if hasattr(check_func, "__await__") else check_func()
                    )
                else:
                    result = {"status": "healthy"}

                results[name] = result

                if result.get("status") != "healthy":
                    overall_status = "unhealthy"

            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = {"status": "unhealthy", "error": str(e)}
                overall_status = "unhealthy"

        return {
            "status": overall_status,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global health checker instance
health_checker = HealthChecker()


def register_health_check(name: str, check_func):
    """Register a health check."""
    health_checker.register_check(name, check_func)


async def get_health_status() -> Dict[str, Any]:
    """Get overall health status."""
    return await health_checker.run_checks()
