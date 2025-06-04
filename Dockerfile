# Multi-stage Docker build for OpenPypi
# Production-ready with security, performance, and debugging optimizations

ARG PYTHON_VERSION=3.11
ARG POETRY_VERSION=1.7.0

#==============================================================================
# Base stage: Common dependencies and setup
#==============================================================================
FROM python:${PYTHON_VERSION}-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 openpypi \
    && useradd --uid 1000 --gid openpypi --shell /bin/bash --create-home openpypi

# Install Poetry
RUN pip install poetry==${POETRY_VERSION}

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

#==============================================================================
# Development stage: For development and testing
#==============================================================================
FROM base as development

# Install all dependencies including dev dependencies
RUN poetry install --with dev,docs,test && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY --chown=openpypi:openpypi . .

# Switch to non-root user
USER openpypi

# Expose development port
EXPOSE 8000

# Development command with auto-reload
CMD ["poetry", "run", "uvicorn", "openpypi.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

#==============================================================================
# Builder stage: Build the application
#==============================================================================
FROM base as builder

# Install only production dependencies
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY . .

# Build the application
RUN poetry build

#==============================================================================
# Production stage: Optimized for production deployment
#==============================================================================
FROM python:${PYTHON_VERSION}-slim as production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    PYTHONPATH=/app

# Install only essential system packages and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    redis-tools \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Create non-root user
RUN groupadd --gid 1000 openpypi \
    && useradd --uid 1000 --gid openpypi --shell /bin/bash --create-home openpypi

# Create application directories
RUN mkdir -p /app /app/logs /app/uploads /app/cache \
    && chown -R openpypi:openpypi /app

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder --chown=openpypi:openpypi /app/dist/*.whl /tmp/

# Install the application
RUN pip install /tmp/*.whl gunicorn[gthread] uvicorn[standard] \
    && rm -rf /tmp/*.whl /root/.cache

# Copy additional files
COPY --chown=openpypi:openpypi scripts/ ./scripts/
COPY --chown=openpypi:openpypi docker/ ./docker/

# Switch to non-root user
USER openpypi

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose production port
EXPOSE 8000

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Production command with Gunicorn
CMD ["gunicorn", "--config", "docker/gunicorn.conf.py", "openpypi.api.app:app"]

#==============================================================================
# Test stage: For running tests in CI/CD
#==============================================================================
FROM development as test

# Copy test files
COPY --chown=openpypi:openpypi tests/ ./tests/

# Run tests
RUN poetry run pytest tests/ \
    --cov=openpypi \
    --cov-report=xml \
    --cov-report=term-missing \
    --junit-xml=test-results.xml

#==============================================================================
# Security scan stage: For security vulnerability scanning
#==============================================================================
FROM production as security-scan

# Switch back to root for security tools installation
USER root

# Install security scanning tools
RUN pip install safety bandit semgrep

# Copy source for scanning
COPY --chown=openpypi:openpypi src/ ./src/

# Run security scans
RUN safety check \
    && bandit -r src/ -f json -o security-report.json \
    && semgrep --config=auto src/ --json --output=semgrep-report.json

# Switch back to non-root user
USER openpypi 