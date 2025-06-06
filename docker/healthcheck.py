#!/usr/bin/env python3
"""
Docker healthcheck script for OpenPypi API server.
"""

import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict


def check_api_health() -> Dict[str, Any]:
    """Check API server health."""
    host = os.getenv("OPENPYPI_HOST", "0.0.0.0")
    port = os.getenv("OPENPYPI_PORT", "8000")

    if host == "0.0.0.0":
        host = "localhost"

    url = f"http://{host}:{port}/health"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 200:
                return {
                    "status": "healthy",
                    "code": response.status,
                    "message": "API server is responding",
                }
            else:
                return {
                    "status": "unhealthy",
                    "code": response.status,
                    "message": f"API server returned status {response.status}",
                }
    except urllib.error.URLError as e:
        return {
            "status": "unhealthy",
            "code": None,
            "message": f"Failed to connect to API server: {e}",
        }
    except Exception as e:
        return {"status": "unhealthy", "code": None, "message": f"Unexpected error: {e}"}


def check_filesystem() -> Dict[str, Any]:
    """Check filesystem health."""
    required_dirs = ["/app/data", "/app/logs", "/app/config"]

    for directory in required_dirs:
        if not os.path.exists(directory):
            return {"status": "unhealthy", "message": f"Required directory missing: {directory}"}

        if not os.access(directory, os.W_OK):
            return {"status": "unhealthy", "message": f"Cannot write to directory: {directory}"}

    return {"status": "healthy", "message": "Filesystem checks passed"}


def check_memory() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        import psutil

        memory = psutil.virtual_memory()

        # Warning if memory usage is above 90%
        if memory.percent > 90:
            return {"status": "warning", "message": f"High memory usage: {memory.percent:.1f}%"}

        return {"status": "healthy", "message": f"Memory usage: {memory.percent:.1f}%"}
    except ImportError:
        return {"status": "unknown", "message": "psutil not available for memory check"}


def main():
    """Run health checks and exit with appropriate code."""
    checks = {"api": check_api_health(), "filesystem": check_filesystem(), "memory": check_memory()}

    # Check if any critical checks failed
    critical_checks = ["api", "filesystem"]
    failed_checks = []

    for check_name in critical_checks:
        if checks[check_name]["status"] == "unhealthy":
            failed_checks.append(check_name)

    if failed_checks:
        print(f"UNHEALTHY: Failed checks: {', '.join(failed_checks)}")
        for check_name, result in checks.items():
            print(f"  {check_name}: {result['message']}")
        sys.exit(1)

    # Check for warnings
    warning_checks = [name for name, result in checks.items() if result["status"] == "warning"]

    if warning_checks:
        print(f"HEALTHY (with warnings): {', '.join(warning_checks)}")
        for check_name, result in checks.items():
            print(f"  {check_name}: {result['message']}")
    else:
        print("HEALTHY: All checks passed")
        for check_name, result in checks.items():
            print(f"  {check_name}: {result['message']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
