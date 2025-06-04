# OpenPypi - Complete Python Project Generator

[![CI/CD Pipeline](https://github.com/openpypi/openpypi/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/openpypi/openpypi/actions)
[![codecov](https://codecov.io/gh/openpypi/openpypi/branch/main/graph/badge.svg)](https://codecov.io/gh/openpypi/openpypi)
[![PyPI version](https://badge.fury.io/py/openpypi.svg)](https://badge.fury.io/py/openpypi)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**OpenPypi** is a comprehensive, production-ready Python project generator with AI integration, FastAPI web framework, Docker containerization, and enterprise-grade CI/CD pipelines. Generate complete, modern Python projects with just a few commands.

## FEATURES

### Core Functionality
- **AI-Powered Generation**: OpenAI integration for intelligent project scaffolding
- **Web Framework Integration**: Modern async web framework with automatic API documentation
- **Container Support**: Multi-stage production-ready Dockerfiles and docker-compose
- **Performance Optimized**: Advanced middleware with rate limiting, caching, and monitoring
- **Enterprise Security**: Comprehensive security headers, authentication, and audit logging
- **Real-time Monitoring**: System metrics, health checks, and performance tracking
- **Database Integration**: SQLAlchemy models with Alembic migrations
- **Comprehensive Testing**: pytest, coverage, performance, and security testing
- **Auto Documentation**: Sphinx documentation with API reference
- **CI/CD Pipelines**: GitHub Actions with multi-stage deployments

### Advanced Features
- **Load Testing**: Locust-based performance testing framework
- **Database Management**: Full ORM with migrations and connection pooling  
- **Caching Layer**: Redis integration for performance optimization
- **Audit Logging**: Complete user action tracking and compliance
- **API Versioning**: Backward-compatible API evolution
- **Multi-cloud Deployment**: AWS, GCP, Azure, and Kubernetes support
- **Security Scanning**: Bandit, Safety, and Semgrep integration
- **Code Quality**: Black, isort, flake8, pylint, and mypy

## INSTALLATION

### Quick Start

```bash
pip install openpypi
```

### Development Installation

```bash
git clone https://github.com/openpypi/openpypi.git
cd openpypi
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev]
```

### Docker Installation

```bash
docker pull openpypi/openpypi:latest
docker run -p 8000:8000 openpypi/openpypi:latest
```

## USAGE

### Command Line Interface

```bash
# Generate a basic project
openpypi generate my-project --description "My awesome project"

# Generate with FastAPI
openpypi generate my-api --fastapi --docker --github-actions

# Generate with AI assistance
openpypi generate my-ai-project --openai --idea "A web scraping service"

# Show available options
openpypi --help
```

### Web API

Start the FastAPI server:

```bash
# Development
uvicorn openpypi.api.app:app --reload

# Production
gunicorn openpypi.api.app:app -w 4 -k uvicorn.workers.UvicornWorker
```

#### API Examples

```bash
# Health check
curl http://localhost:8000/health

# Generate project synchronously
curl -X POST http://localhost:8000/generate/sync \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "description": "A test project",
    "author": "John Doe",
    "email": "john@example.com"
  }'

# Generate project asynchronously
curl -X POST http://localhost:8000/generate/async \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-async-project",
    "description": "An async test project",
    "author": "Jane Smith",
    "email": "jane@example.com",
    "options": {
      "use_fastapi": true,
      "use_docker": true,
      "test_framework": "pytest"
    }
  }'

# Check task status
curl http://localhost:8000/generate/status/{task_id}

# Get system metrics
curl http://localhost:8000/monitoring/metrics
```

### Python API

```python
from openpypi.core.generator import ProjectGenerator
from openpypi.core.config import Config

# Create configuration
config = Config(
    project_name="my-awesome-project",
    package_name="my_package",
    author="Your Name",
    email="your.email@example.com",
    use_fastapi=True,
    use_docker=True,
    use_openai=True
)

# Generate project
generator = ProjectGenerator(config)
result = generator.generate()

print(f"Project created at: {result['project_dir']}")
print(f"Files created: {len(result['files_created'])}")
```

## ARCHITECTURE

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   CLI Interface │    │  Web Dashboard  │
│                 │    │                 │    │                 │
│  • REST API     │    │  • Commands     │    │  • UI/UX        │
│  • WebSockets   │    │  • Scripts      │    │  • Monitoring   │
│  • Auth         │    │  • Automation   │    │  • Analytics    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────────┐
         │                Core Engine                          │
         │                                                     │
         │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
         │  │  Generator  │  │   Config    │  │ Orchestrator│  │
         │  │             │  │             │  │             │  │
         │  │ • Templates │  │ • Settings  │  │ • Workflow  │  │
         │  │ • Rendering │  │ • Validation│  │ • Stages    │  │
         │  │ • Files     │  │ • Profiles  │  │ • Pipeline  │  │
         │  └─────────────┘  └─────────────┘  └─────────────┘  │
         └─────────────────────────────────────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────────┐
         │                 Data Layer                          │
         │                                                     │
         │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
         │  │  Database   │  │    Cache    │  │  File Store │  │
         │  │             │  │             │  │             │  │
         │  │ • SQLAlchemy│  │ • Redis     │  │ • Templates │  │
         │  │ • PostgreSQL│  │ • Sessions  │  │ • Artifacts │  │
         │  │ • Migrations│  │ • Metrics   │  │ • Logs      │  │
         │  └─────────────┘  └─────────────┘  └─────────────┘  │
         └─────────────────────────────────────────────────────┘
```

### Request Flow

```
User Request → Middleware → Authentication → Rate Limiting → 
Business Logic → Database → Cache → Response → Logging → Metrics
```

## TESTING

### Run All Tests

```bash
# Run test suite
pytest

# Run with coverage
pytest --cov=openpypi --cov-report=html

# Run specific test types
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/api/          # API tests
pytest tests/performance/  # Performance tests
```

### Performance Testing

```bash
# Install performance testing dependencies
pip install locust

# Run load tests
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Run headless performance test
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users=50 --spawn-rate=5 --run-time=300s --headless
```

### Security Testing

```bash
# Security scan
bandit -r src/

# Vulnerability check
safety check

# Advanced security analysis
semgrep --config=auto src/
```

## DOCKER DEPLOYMENT

### Multi-stage Dockerfile

The project includes a sophisticated multi-stage Dockerfile for different environments:

```bash
# Development
docker build --target development -t openpypi:dev .

# Production
docker build --target production -t openpypi:prod .

# Testing
docker build --target testing -t openpypi:test .

# Documentation
docker build --target docs -t openpypi:docs .

# Minimal runtime (distroless)
docker build --target distroless -t openpypi:minimal .
```

### Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.enhanced.yml up

# Production deployment
docker-compose -f docker-compose.enhanced.yml -f docker-compose.prod.yml up
```

## KUBERNETES DEPLOYMENT

### Deploy to Kubernetes

```bash
# Apply namespace
kubectl apply -f k8s/namespace.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods -n openpypi
kubectl get services -n openpypi
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/live

# Readiness probe  
curl http://localhost:8000/ready

# Detailed health
curl http://localhost:8000/health/detailed
```

## MONITORING & OBSERVABILITY

### System Metrics

```bash
# Application metrics
curl http://localhost:8000/monitoring/metrics

# System resources
curl http://localhost:8000/monitoring/metrics/system

# Application performance
curl http://localhost:8000/monitoring/metrics/application
```

### Database Monitoring

```python
from openpypi.database import get_database_manager

db_manager = get_database_manager()
health = db_manager.health_check()
print(f"Database status: {health['status']}")
```

### Performance Monitoring

The system includes comprehensive performance monitoring:

- **Request/Response metrics**: Latency, throughput, error rates
- **System resources**: CPU, memory, disk, network usage  
- **Database performance**: Connection pooling, query performance
- **Cache metrics**: Hit rates, eviction policies
- **Custom business metrics**: Project generation success rates

## CONFIGURATION

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/openpypi
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
API_KEYS=key1,key2,key3

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

### Configuration File

```python
# config.py
from openpypi.core.config import Config

config = Config(
    # Project settings
    project_name="my-project",
    package_name="my_package", 
    author="Your Name",
    email="your.email@example.com",
    
    # Features
    use_fastapi=True,
    use_docker=True,
    use_openai=True,
    use_github_actions=True,
    
    # Testing
    create_tests=True,
    test_framework="pytest",
    
    # Database
    use_database=True,
    database_type="postgresql",
    
    # Deployment
    cloud_provider="aws",
    kubernetes_enabled=True
)
```

## SECURITY FEATURES

### Authentication & Authorization

- **API Key Authentication**: Secure API access with rate limiting
- **JWT Tokens**: Stateless authentication for web applications  
- **Role-based Access Control**: Fine-grained permissions
- **Audit Logging**: Complete action tracking and compliance

### Security Headers

- **HTTPS Enforcement**: HSTS headers and secure redirects
- **XSS Protection**: Content Security Policy and XSS filtering
- **CSRF Protection**: Token-based CSRF prevention
- **Click-jacking Prevention**: X-Frame-Options headers

### Data Protection

- **Input Validation**: Comprehensive request validation
- **SQL Injection Prevention**: Parameterized queries and ORM
- **Secret Management**: Environment-based configuration
- **Encryption**: At-rest and in-transit data encryption

## PERFORMANCE OPTIMIZATION

### Caching Strategy

```python
# Redis caching
from openpypi.cache import CacheManager

cache = CacheManager()

# Cache generation results
@cache.memoize(timeout=3600)
def generate_project(config):
    return expensive_generation_operation(config)
```

### Database Optimization

- **Connection Pooling**: Optimized database connections
- **Query Optimization**: Indexed queries and eager loading
- **Read Replicas**: Separate read/write operations
- **Migration Management**: Zero-downtime schema changes

### API Performance

- **Response Compression**: GZip compression for API responses
- **Request Batching**: Bulk operations for efficiency
- **Async Processing**: Non-blocking I/O operations
- **Rate Limiting**: Intelligent throttling and queuing

## DEPLOYMENT OPTIONS

### Cloud Platforms

#### AWS Deployment

```bash
# ECS Deployment
aws ecs create-cluster --cluster-name openpypi
aws ecs create-service --cluster openpypi --service-name openpypi-api

# Lambda Deployment  
sam build
sam deploy --guided
```

#### Google Cloud Platform

```bash
# Cloud Run
gcloud run deploy openpypi --source .

# GKE
gcloud container clusters create openpypi-cluster
kubectl apply -f k8s/
```

#### Azure

```bash
# Container Instances
az container create --resource-group myResourceGroup \
  --name openpypi --image openpypi/openpypi:latest

# Kubernetes Service
az aks create --resource-group myResourceGroup --name openpypi-aks
```

### Infrastructure as Code

```bash
# Terraform
cd terraform/
terraform init
terraform plan
terraform apply

# Ansible
ansible-playbook -i inventory playbooks/deploy.yml
```

## CI/CD PIPELINE

### GitHub Actions Workflow

The project includes a comprehensive CI/CD pipeline:

1. **Code Quality**: Linting, formatting, type checking
2. **Security Scanning**: Vulnerability and security analysis  
3. **Testing**: Unit, integration, API, and performance tests
4. **Docker Build**: Multi-arch container builds with security scanning
5. **Documentation**: Automatic documentation generation
6. **Release**: Automated PyPI and Docker Hub publishing
7. **Deployment**: Staging and production deployments

### Pipeline Stages

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  security:      # Security and vulnerability scanning
  code-quality:  # Code formatting and linting  
  test:         # Test suite across multiple Python versions
  performance:  # Load testing and benchmarks
  docker:       # Container builds and security scans
  docs:         # Documentation building and deployment
  release:      # Package and container publishing
  deploy:       # Production deployment
```

## DOCUMENTATION

### API Documentation

The FastAPI application provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Code Documentation

```bash
# Build documentation
cd docs/
make html

# Serve documentation
python -m http.server 8080 --directory _build/html
```

### Examples and Tutorials

- [Getting Started Guide](docs/getting-started.md)
- [API Reference](docs/api-reference.md)
- [Configuration Guide](docs/configuration.md)
- [Deployment Guide](docs/deployment.md)
- [Performance Tuning](docs/performance.md)
- [Security Best Practices](docs/security.md)

## CONTRIBUTING

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/openpypi/openpypi.git
cd openpypi

# Setup development environment
make dev-setup

# Run pre-commit hooks
pre-commit install

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

### Code Style

We use the following tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting  
- **flake8**: Linting
- **pylint**: Advanced linting
- **mypy**: Type checking
- **pre-commit**: Git hooks

## LICENSE

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ACKNOWLEDGMENTS

- **FastAPI**: Modern web framework for building APIs
- **SQLAlchemy**: SQL toolkit and Object-Relational Mapping
- **Docker**: Containerization platform
- **OpenAI**: AI-powered code generation
- **GitHub Actions**: CI/CD automation
- **All Contributors**: Thanks to everyone who has contributed!

## SUPPORT

- **Documentation**: [https://openpypi.readthedocs.io](https://openpypi.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/openpypi/openpypi/issues)
- **Discussions**: [GitHub Discussions](https://github.com/openpypi/openpypi/discussions)
- **Email**: [nikjois@llamasearch.ai](mailto:nikjois@llamasearch.ai)

## ROADMAP

### Upcoming Features

- [ ] **AI Code Review**: Automated code quality suggestions
- [ ] **Plugin System**: Extensible architecture for custom generators
- [ ] **Visual Project Builder**: Web-based drag-and-drop interface
- [ ] **Multi-language Support**: Support for other programming languages
- [ ] **Cloud IDE Integration**: GitHub Codespaces, GitPod integration
- [ ] **Advanced Analytics**: Project success metrics and insights
- [ ] **Team Collaboration**: Shared projects and team management
- [ ] **Enterprise Features**: SSO, compliance, and audit features

### Version History

- **v0.1.0**: Initial release with basic project generation
- **v0.2.0**: FastAPI integration and Docker support
- [ ] **v0.3.0**: AI integration and advanced templates
- [ ] **v0.4.0**: Database integration and monitoring
- [ ] **v0.5.0**: Performance optimization and security enhancements
- [ ] **v1.0.0**: Production-ready release (upcoming)

---

**Please star this repository if you find it useful!** 