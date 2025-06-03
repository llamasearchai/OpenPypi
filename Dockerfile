# Base image for production
FROM python:3.11-slim as production-base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.7.1 
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Install poetry
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only necessary files for dependency installation
COPY poetry.lock pyproject.toml README.md ./

# Install production dependencies
RUN poetry install --no-interaction --no-ansi --no-dev

# --- Development/Builder Stage ---
FROM python:3.11 as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=true 
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Install poetry (can be cached if base image doesn't change often)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml README.md ./

# Install all dependencies including development ones
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . .

# --- Final Production Stage ---
FROM production-base as final

WORKDIR /app

# Copy installed dependencies from production-base stage
COPY --from=production-base /app /app
# Copy application code from builder stage (excluding dev dependencies potentially)
# This assumes your 'src' is correctly picked up by poetry or you adjust as needed
COPY --from=builder /app/src /app/src
COPY --from=builder /app/main.py /app/main.py # If you have a main.py at root for uvicorn
COPY --from=builder /app/openpypi.toml /app/openpypi.toml # Example config file

# Create a non-root user and switch to it
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Copy application files as appuser to ensure correct permissions
COPY --chown=appuser:appuser --from=builder /app/src ./src
# If you have a main.py at root for uvicorn or other top-level files:
# COPY --chown=appuser:appuser --from=builder /app/main.py .
# COPY --chown=appuser:appuser --from=builder /app/openpypi.toml .

# Ensure the entrypoint script exists and is executable if you use one
# COPY --chmod=0755 entrypoint.sh /entrypoint.sh
# ENTRYPOINT ["/entrypoint.sh"]

# Expose port and set default command
EXPOSE 8000

# The command should refer to the installed package, e.g., openpypi.api.app:app
# Ensure your project structure and pyproject.toml make this accessible.
# If using poetry run:
# CMD ["poetry", "run", "uvicorn", "openpypi.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
# Or direct uvicorn if path is correctly set up in the environment:
CMD ["uvicorn", "openpypi.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Healthcheck (ensure /health endpoint exists and works)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1 