"""
Stage 6: Deployment - Deploy the generated package to various platforms.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import getpass

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger
from twine.commands.upload import upload as twine_upload
from twine.settings import Settings

logger = get_logger(__name__)


class DeployerStage(BaseStage):
    """
    Stage 6: Deployment

    This stage handles deployment of the generated package to various platforms
    including PyPI, Docker registries, cloud platforms, and GitHub releases.
    """

    async def execute(self, context: PackageContext) -> None:
        """Execute the deployment stage."""
        self.log_stage_start()

        try:
            # Get previous stage outputs
            concept_data = context.get_stage_output("p1_concept") or {}
            validation_data = context.get_stage_output("p4_validation") or {}
            documentation_data = context.get_stage_output("p5_documentation") or {}

            # Create deployment configurations
            deployment_configs = await self._create_deployment_configs(context, concept_data)

            # Generate Docker configuration
            docker_config = await self._generate_docker_config(context)

            # Create CI/CD pipelines
            cicd_config = await self._create_cicd_pipelines(context)

            # Generate deployment scripts
            deployment_scripts = await self._generate_deployment_scripts(context)

            # Create cloud deployment configurations
            cloud_configs = await self._create_cloud_configs(context)

            # Combine all deployment data
            deployment_data = {
                "deployment_configs": deployment_configs,
                "docker": docker_config,
                "cicd": cicd_config,
                "scripts": deployment_scripts,
                "cloud": cloud_configs,
                "deployment_ready": True,
            }

            if await self.validate_output(deployment_data):
                # Write deployment files
                await self._write_deployment_files(context, deployment_data)

                # Create deployment documentation
                await self._create_deployment_docs(context, deployment_data)

                # Store stage output
                context.set_stage_output("p6_deployment", deployment_data)

                self.log_stage_end()
            else:
                raise ValueError("Deployment configuration validation failed")

            # Get PyPI token securely
            if not context.config.get('PYPI_TOKEN'):
                context.config['PYPI_TOKEN'] = getpass.getpass("Enter your PyPI API token: ")
                
            # Configure twine
            settings = Settings(
                username='__token__',
                password=context.config['PYPI_TOKEN'],
                repository_url="https://upload.pypi.org/legacy/",
                disable_progress_bar=False,
            )

            # Upload package
            dist_path = context.output_dir / 'dist'
            if not list(dist_path.glob('*.tar.gz')):
                self.log_stage_error("No distribution files found. Run build first.")
                return

            result = twine_upload(
                settings,
                [str(p) for p in dist_path.glob('*')]
            )
            
            if result:
                self.log_stage_info(f"Successfully published {len(result)} packages")
            else:
                self.log_stage_error("Package upload failed")

        except Exception as e:
            self.log_stage_error(f"Publishing failed: {str(e)}")
            raise

    async def _create_deployment_configs(
        self, context: PackageContext, concept_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create deployment configurations."""
        deployment_targets = concept_data.get("deployment_targets", ["pypi", "docker"])

        configs = {
            "targets": deployment_targets,
            "environment": context.config.get("deployment", {}).get("environment", "production"),
            "auto_deploy": context.config.get("deployment", {}).get("auto_deploy", False),
            "notifications": context.config.get("deployment", {}).get("notifications", []),
        }

        logger.info(f"Created deployment configs for targets: {deployment_targets}")
        return configs

    async def _generate_docker_config(self, context: PackageContext) -> Dict[str, str]:
        """Generate Docker configuration files."""
        dockerfile_content = self._generate_dockerfile(context)
        dockerignore_content = self._generate_dockerignore()
        docker_compose_content = self._generate_docker_compose(context)

        return {
            "Dockerfile": dockerfile_content,
            ".dockerignore": dockerignore_content,
            "docker-compose.yml": docker_compose_content,
            "docker-compose.prod.yml": self._generate_docker_compose_prod(context),
        }

    def _generate_dockerfile(self, context: PackageContext) -> str:
        """Generate Dockerfile content."""
        return f"""# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        build-essential \\
        curl \\
        git \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Install package in development mode
RUN pip install -e .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \\
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "{context.package_name}.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    def _generate_dockerignore(self) -> str:
        """Generate .dockerignore content."""
        return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Git
.git/
.gitignore

# Documentation
docs/_build/

# Testing
.coverage
.pytest_cache/
htmlcov/

# CI/CD
.github/
.gitlab-ci.yml

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Logs
*.log
logs/

# Temporary files
*.tmp
temp/
"""

    def _generate_docker_compose(self, context: PackageContext) -> str:
        """Generate docker-compose.yml content."""
        return f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    volumes:
      - .:/app
      - /app/venv
    depends_on:
      - db
      - redis
    networks:
      - {context.package_name}-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: {context.package_name}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - {context.package_name}-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - {context.package_name}-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    networks:
      - {context.package_name}-network

volumes:
  postgres_data:

networks:
  {context.package_name}-network:
    driver: bridge
"""

    def _generate_docker_compose_prod(self, context: PackageContext) -> str:
        """Generate production docker-compose.yml content."""
        return f"""version: '3.8'

services:
  app:
    image: {context.package_name}:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DATABASE_URL=postgresql://postgres:${{POSTGRES_PASSWORD}}@db:5432/{context.package_name}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    networks:
      - {context.package_name}-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: {context.package_name}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD}}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - {context.package_name}-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - {context.package_name}-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - {context.package_name}-network

volumes:
  postgres_data:

networks:
  {context.package_name}-network:
    driver: bridge
"""

    async def _create_cicd_pipelines(self, context: PackageContext) -> Dict[str, str]:
        """Create CI/CD pipeline configurations."""
        github_workflow = self._generate_github_workflow(context)
        gitlab_ci = self._generate_gitlab_ci(context)

        return {"github_workflow": github_workflow, "gitlab_ci": gitlab_ci}

    def _generate_github_workflow(self, context: PackageContext) -> str:
        """Generate GitHub Actions workflow."""
        return f"""name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  release:
    types: [ published ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    
    - name: Lint with flake8
      run: |
        flake8 src/ tests/
    
    - name: Check code formatting with black
      run: |
        black --check src/ tests/
    
    - name: Sort imports with isort
      run: |
        isort --check-only src/ tests/
    
    - name: Type check with mypy
      run: |
        mypy src/
    
    - name: Security check with bandit
      run: |
        bandit -r src/
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src/ --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip build twine
    
    - name: Build package
      run: |
        python -m build
    
    - name: Check package
      run: |
        twine check dist/*
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{{{ secrets.PYPI_API_TOKEN }}}}
      run: |
        twine upload dist/*

  docker:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.event_name == 'release'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{{{ secrets.DOCKER_USERNAME }}}}
        password: ${{{{ secrets.DOCKER_PASSWORD }}}}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: {context.package_name}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{{{version}}}}
          type=semver,pattern={{{{major}}}}.{{{{minor}}}}
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{{{ steps.meta.outputs.tags }}}}
        labels: ${{{{ steps.meta.outputs.labels }}}}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: [build, docker]
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to production
      run: |
        echo "Deploying to production..."
        # Add your deployment script here
"""

    def _generate_gitlab_ci(self, context: PackageContext) -> str:
        """Generate GitLab CI configuration."""
        return f"""stages:
  - test
  - security
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  DOCKER_TLS_CERTDIR: "/certs"

cache:
  paths:
    - .cache/pip/
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install --upgrade pip
  - pip install -e .[dev]

test:
  stage: test
  image: python:3.11
  script:
    - flake8 src/ tests/
    - black --check src/ tests/
    - isort --check-only src/ tests/
    - mypy src/
    - pytest tests/ --cov=src/ --cov-report=xml --cov-report=term
  coverage: '/(?i)total.*? (100(?:\\.0+)?\\%|[1-9]?\\d(?:\\.\\d+)?\\%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.8", "3.9", "3.10", "3.11", "3.12"]
  image: python:$PYTHON_VERSION

security:
  stage: security
  image: python:3.11
  script:
    - bandit -r src/
    - safety check
    - pip-audit
  allow_failure: true

build_package:
  stage: build
  image: python:3.11
  script:
    - pip install build twine
    - python -m build
    - twine check dist/*
  artifacts:
    paths:
      - dist/
  only:
    - tags

build_docker:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $CI_REGISTRY_IMAGE:{context.package_name} .
    - docker push $CI_REGISTRY_IMAGE:{context.package_name}
  only:
    - main
    - tags

deploy_pypi:
  stage: deploy
  image: python:3.11
  script:
    - pip install twine
    - twine upload dist/*
  environment:
    name: pypi
    url: https://pypi.org/project/{context.package_name}/
  only:
    - tags
  when: manual

deploy_production:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache curl
  script:
    - echo "Deploying to production..."
    # Add your deployment script here
  environment:
    name: production
    url: https://your-production-url.com
  only:
    - tags
  when: manual
"""

    async def _generate_deployment_scripts(self, context: PackageContext) -> Dict[str, str]:
        """Generate deployment scripts."""
        deploy_script = self._generate_deploy_script(context)
        setup_script = self._generate_setup_script(context)

        return {"deploy.sh": deploy_script, "setup.sh": setup_script}

    def _generate_deploy_script(self, context: PackageContext) -> str:
        """Generate deployment script."""
        return f"""#!/bin/bash

# Deployment script for {context.package_name}
set -e

echo "Starting deployment of {context.package_name}..."

# Configuration
PROJECT_NAME="{context.package_name}"
DOCKER_IMAGE="${{PROJECT_NAME}}:latest"
CONTAINER_NAME="${{PROJECT_NAME}}-app"
NETWORK_NAME="${{PROJECT_NAME}}-network"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Helper functions
log_info() {{
    echo -e "${{GREEN}}[INFO]${{NC}} $1"
}}

log_warn() {{
    echo -e "${{YELLOW}}[WARN]${{NC}} $1"
}}

log_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Pull latest image
log_info "Pulling latest Docker image..."
docker pull $DOCKER_IMAGE

# Stop existing container
if docker ps -q -f name=$CONTAINER_NAME > /dev/null; then
    log_info "Stopping existing container..."
    docker stop $CONTAINER_NAME
fi

# Remove existing container
if docker ps -aq -f name=$CONTAINER_NAME > /dev/null; then
    log_info "Removing existing container..."
    docker rm $CONTAINER_NAME
fi

# Create network if it doesn't exist
if ! docker network ls | grep -q $NETWORK_NAME; then
    log_info "Creating Docker network..."
    docker network create $NETWORK_NAME
fi

# Start new container
log_info "Starting new container..."
docker run -d \\
    --name $CONTAINER_NAME \\
    --network $NETWORK_NAME \\
    -p 8000:8000 \\
    --restart unless-stopped \\
    $DOCKER_IMAGE

# Wait for container to be healthy
log_info "Waiting for container to be healthy..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec $CONTAINER_NAME curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Container is healthy!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    log_error "Container failed to become healthy within 60 seconds"
    docker logs $CONTAINER_NAME
    exit 1
fi

log_info "Deployment completed successfully!"
log_info "Application is running at http://localhost:8000"
"""

    def _generate_setup_script(self, context: PackageContext) -> str:
        """Generate setup script."""
        return f"""#!/bin/bash

# Setup script for {context.package_name} development environment
set -e

echo "Setting up {context.package_name} development environment..."

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

log_info() {{
    echo -e "${{GREEN}}[INFO]${{NC}} $1"
}}

log_warn() {{
    echo -e "${{YELLOW}}[WARN]${{NC}} $1"
}}

log_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
log_info "Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
log_info "Installing dependencies..."
pip install -e .[dev]

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    log_info "Installing pre-commit hooks..."
    pre-commit install
fi

# Run initial tests
log_info "Running initial tests..."
pytest tests/ --tb=short

# Check code quality
log_info "Checking code quality..."
flake8 src/ tests/ || log_warn "Flake8 issues found"
black --check src/ tests/ || log_warn "Black formatting issues found"
isort --check-only src/ tests/ || log_warn "Import sorting issues found"

log_info "Setup completed successfully!"
log_info "To activate the virtual environment, run: source venv/bin/activate"
log_info "To run the development server, run: uvicorn {context.package_name}.main:app --reload"
"""

    async def _create_cloud_configs(self, context: PackageContext) -> Dict[str, Any]:
        """Create cloud deployment configurations."""
        return {
            "heroku": self._generate_heroku_config(context),
            "aws": self._generate_aws_config(context),
            "gcp": self._generate_gcp_config(context),
            "azure": self._generate_azure_config(context),
        }

    def _generate_heroku_config(self, context: PackageContext) -> Dict[str, str]:
        """Generate Heroku configuration."""
        procfile = f"web: uvicorn {context.package_name}.main:app --host 0.0.0.0 --port $PORT"

        app_json = {
            "name": context.package_name,
            "description": f"A Python application built with {context.package_name}",
            "repository": f"https://github.com/yourusername/{context.package_name}",
            "keywords": ["python", "fastapi", "web"],
            "addons": ["heroku-postgresql:hobby-dev", "heroku-redis:hobby-dev"],
            "env": {"ENVIRONMENT": "production", "DEBUG": "false"},
            "formation": {"web": {"quantity": 1, "size": "hobby"}},
        }

        return {"Procfile": procfile, "app.json": json.dumps(app_json, indent=2)}

    def _generate_aws_config(self, context: PackageContext) -> Dict[str, str]:
        """Generate AWS deployment configuration."""
        # Simplified AWS configuration - would need more detailed setup
        return {
            "buildspec.yml": f"""version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t {context.package_name} .
      - docker tag {context.package_name}:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/{context.package_name}:latest
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/{context.package_name}:latest
"""
        }

    def _generate_gcp_config(self, context: PackageContext) -> Dict[str, str]:
        """Generate Google Cloud Platform configuration."""
        return {
            "cloudbuild.yaml": f"""steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/{context.package_name}', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/{context.package_name}']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', '{context.package_name}', '--image', 'gcr.io/$PROJECT_ID/{context.package_name}', '--region', 'us-central1', '--platform', 'managed']
"""
        }

    def _generate_azure_config(self, context: PackageContext) -> Dict[str, str]:
        """Generate Azure deployment configuration."""
        return {
            "azure-pipelines.yml": f"""trigger:
- main

pool:
  vmImage: 'ubuntu-latest'

variables:
  dockerRegistryServiceConnection: 'your-service-connection'
  imageRepository: '{context.package_name}'
  containerRegistry: 'yourregistry.azurecr.io'
  dockerfilePath: '$(Build.SourcesDirectory)/Dockerfile'
  tag: '$(Build.BuildId)'

stages:
- stage: Build
  displayName: Build and push stage
  jobs:
  - job: Build
    displayName: Build
    steps:
    - task: Docker@2
      displayName: Build and push an image to container registry
      inputs:
        command: buildAndPush
        repository: $(imageRepository)
        dockerfile: $(dockerfilePath)
        containerRegistry: $(dockerRegistryServiceConnection)
        tags: |
          $(tag)
"""
        }

    async def _write_deployment_files(
        self, context: PackageContext, deployment_data: Dict[str, Any]
    ) -> None:
        """Write deployment files to the project directory."""
        output_dir = context.output_dir

        # Write Docker files
        docker_config = deployment_data["docker"]
        for filename, content in docker_config.items():
            file_path = output_dir / filename
            file_path.write_text(content)
            logger.info(f"Created {filename}")

        # Write CI/CD files
        cicd_config = deployment_data["cicd"]

        # GitHub workflow
        github_dir = output_dir / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)
        github_workflow_path = github_dir / "ci-cd.yml"
        github_workflow_path.write_text(cicd_config["github_workflow"])
        logger.info("Created GitHub workflow")

        # GitLab CI
        gitlab_ci_path = output_dir / ".gitlab-ci.yml"
        gitlab_ci_path.write_text(cicd_config["gitlab_ci"])
        logger.info("Created GitLab CI configuration")

        # Write deployment scripts
        scripts_dir = output_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        scripts_config = deployment_data["scripts"]
        for filename, content in scripts_config.items():
            script_path = scripts_dir / filename
            script_path.write_text(content)
            script_path.chmod(0o755)  # Make executable
            logger.info(f"Created {filename}")

        # Write cloud configurations
        cloud_config = deployment_data["cloud"]

        # Heroku
        heroku_config = cloud_config["heroku"]
        for filename, content in heroku_config.items():
            file_path = output_dir / filename
            file_path.write_text(content)
            logger.info(f"Created Heroku {filename}")

        # AWS
        aws_config = cloud_config["aws"]
        for filename, content in aws_config.items():
            file_path = output_dir / filename
            file_path.write_text(content)
            logger.info(f"Created AWS {filename}")

        # Other cloud configurations...

    async def _create_deployment_docs(
        self, context: PackageContext, deployment_data: Dict[str, Any]
    ) -> None:
        """Create deployment documentation."""
        deployment_doc = f"""# Deployment Guide for {context.package_name}

This guide covers various deployment options for your {context.package_name} application.

## Quick Start

### Local Development
```bash
# Setup development environment
./scripts/setup.sh

# Run the application
uvicorn {context.package_name}.main:app --reload
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t {context.package_name} .
docker run -p 8000:8000 {context.package_name}

# Or use docker-compose
docker-compose up -d
```

## Deployment Options

### 1. Heroku
1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create {context.package_name}`
4. Deploy: `git push heroku main`

### 2. AWS
- Use the provided `buildspec.yml` for AWS CodeBuild
- Configure ECR repository
- Set up ECS or Lambda deployment

### 3. Google Cloud Platform
- Use the provided `cloudbuild.yaml`
- Deploy to Cloud Run: `gcloud run deploy`

### 4. Azure
- Use the provided `azure-pipelines.yml`
- Configure Azure Container Registry
- Deploy to Azure Container Instances or App Service

## CI/CD Pipelines

### GitHub Actions
The project includes a complete CI/CD pipeline that:
- Runs tests on multiple Python versions
- Checks code quality (linting, formatting, type checking)
- Builds and publishes Docker images
- Deploys to production on releases

### GitLab CI
Similar pipeline for GitLab with:
- Parallel testing
- Security scanning
- Automatic deployment

## Environment Variables

Set the following environment variables for production:

```bash
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=your_database_url
REDIS_URL=your_redis_url
SECRET_KEY=your_secret_key
```

## Monitoring and Health Checks

The application includes:
- Health check endpoint: `/health`
- Metrics endpoint: `/metrics`
- Docker health checks
- Logging configuration

## Security Considerations

- Use secrets management for sensitive data
- Enable HTTPS in production
- Configure rate limiting
- Regular security updates

For more detailed information, see the individual configuration files.
"""

        docs_dir = context.output_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        deployment_doc_path = docs_dir / "deployment.md"
        deployment_doc_path.write_text(deployment_doc)

        logger.info("Created deployment documentation")

    async def validate_output(self, data: Dict[str, Any]) -> bool:
        """Validate the deployment stage output."""
        required_keys = ["deployment_configs", "docker", "cicd", "scripts"]

        for key in required_keys:
            if key not in data:
                logger.error(f"Missing required key in deployment data: {key}")
                return False

        # Validate Docker configuration
        docker_config = data["docker"]
        required_docker_files = ["Dockerfile", ".dockerignore", "docker-compose.yml"]

        for file_name in required_docker_files:
            if file_name not in docker_config:
                logger.error(f"Missing Docker file: {file_name}")
                return False

        logger.info("Deployment stage output validation passed")
        return True
