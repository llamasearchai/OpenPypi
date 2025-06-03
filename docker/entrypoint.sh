#!/bin/bash

# OpenPypi Docker Entrypoint Script
set -e

# Default values
WORKERS=${OPENPYPI_WORKERS:-4}
PORT=${OPENPYPI_PORT:-8000}
HOST=${OPENPYPI_HOST:-0.0.0.0}
LOG_LEVEL=${OPENPYPI_LOG_LEVEL:-info}
TIMEOUT=${OPENPYPI_TIMEOUT:-120}

# Ensure directories exist
mkdir -p /app/data /app/logs /app/config

# Check if running as API server or CLI
if [ "$1" = "api" ] || [ "$1" = "server" ] || [ "$1" = "" ]; then
    echo "Starting OpenPypi API server..."
    echo "Workers: $WORKERS"
    echo "Port: $PORT"
    echo "Host: $HOST"
    echo "Log Level: $LOG_LEVEL"
    
    # Start API server with Gunicorn
    exec gunicorn \
        --bind $HOST:$PORT \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout $TIMEOUT \
        --log-level $LOG_LEVEL \
        --access-logfile /app/logs/access.log \
        --error-logfile /app/logs/error.log \
        --capture-output \
        openpypi.api.app:app

elif [ "$1" = "cli" ]; then
    shift
    echo "Running OpenPypi CLI with args: $@"
    exec openpypi "$@"

elif [ "$1" = "worker" ]; then
    echo "Starting background worker..."
    # Add background worker implementation here
    exec python -m openpypi.worker

elif [ "$1" = "migrate" ]; then
    echo "Running database migrations..."
    # Add migration logic here
    exec python -m openpypi.migrations

elif [ "$1" = "shell" ] || [ "$1" = "bash" ]; then
    echo "Starting interactive shell..."
    exec /bin/bash

else
    echo "Running custom command: $@"
    exec "$@"
fi 