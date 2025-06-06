"""
Gunicorn Configuration for OpenPypi Production Deployment
Optimized for performance, reliability, and monitoring
"""

import multiprocessing
import os
from pathlib import Path

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv("API_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings
timeout = int(os.getenv("WORKER_TIMEOUT", "300"))
keepalive = int(os.getenv("KEEPALIVE_TIMEOUT", "5"))
graceful_timeout = 30

# Process naming
proc_name = "openpypi"

# User and group (run as non-root)
user = "openpypi"
group = "openpypi"

# Logging
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
pidfile = "/tmp/gunicorn.pid"
daemon = False
raw_env = [
    "PYTHONPATH=/app",
]

# SSL/TLS (if certificates are available)
keyfile = os.getenv("SSL_KEYFILE")
certfile = os.getenv("SSL_CERTFILE")

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
preload_app = True
sendfile = True
reuse_port = True

# Worker recycling for memory management
max_requests = 1000
max_requests_jitter = 100


# Monitoring hooks
def when_ready(server):
    """Called just after the server is started."""
    server.log.info("OpenPypi server is ready to accept connections")


def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info("Worker %s received interrupt signal", worker.pid)


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("👶 About to fork worker %s", worker.pid)


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker %s spawned", worker.pid)


def worker_abort(worker):
    """Called when a worker process is killed."""
    worker.log.error("💥 Worker %s aborted", worker.pid)


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("🔄 Forked child, re-executing")


def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug("📥 Processing request: %s %s", req.method, req.path)


def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    worker.log.debug("📤 Completed request: %s %s -> %s", req.method, req.path, resp.status_code)


# Environment variables for the application
raw_env = [
    f"PYTHONPATH=/app",
    f"APP_ENV=production",
    f"WORKERS={workers}",
]

# Reload configuration (development only)
if os.getenv("APP_ENV") == "development":
    reload = True
    reload_extra_files = [
        "/app/src",
        "/app/pyproject.toml",
    ]
