#!/bin/bash

# Comprehensive build and test script for OpenPypi
# Ensures everything works correctly with complete CI/CD integration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    log_error "Must be run from the project root directory"
    exit 1
fi

log_info "Starting comprehensive build and test process..."

# 1. Environment Setup
log_info "Setting up environment..."
python -m pip install --upgrade pip setuptools wheel

# Install development dependencies
log_info "Installing development dependencies..."
pip install -r requirements-dev.txt

# Install the project in editable mode
log_info "Installing project in editable mode..."
pip install -e .

# 2. Code Quality Checks
log_info "Running code quality checks..."

# Format code with black
log_info "Formatting code with black..."
black src/ tests/ --line-length 100

# Sort imports with isort
log_info "Sorting imports with isort..."
isort src/ tests/ --profile black

# Check code style with flake8
log_info "Checking code style with flake8..."
flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

# Type checking with mypy
log_info "Running type checks with mypy..."
mypy src/ --ignore-missing-imports

# Security checks with bandit
log_info "Running security checks with bandit..."
bandit -r src/ -f json -o security-report.json || log_warning "Bandit found potential security issues"

# 3. Testing
log_info "Running comprehensive test suite..."

# Unit tests with coverage
log_info "Running unit tests with coverage..."
pytest tests/unit/ \
    --cov=openpypi \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --junit-xml=test-results.xml \
    -v

# Integration tests
log_info "Running integration tests..."
pytest tests/integration/ -v --tb=short || log_warning "Some integration tests failed"

# Performance tests (if available)
if [ -d "tests/performance" ]; then
    log_info "Running performance tests..."
    pytest tests/performance/ -v --benchmark-enable || log_warning "Performance tests failed"
fi

# Provider tests with benchmarks
log_info "Running enhanced provider tests..."
pytest tests/unit/providers/test_providers_enhanced.py \
    -v \
    -m "not stress" \
    --benchmark-enable \
    --tb=short

# 4. Build Package
log_info "Building package..."
python -m build --sdist --wheel

# 5. Docker Integration (if Docker is available)
if command -v docker &> /dev/null; then
    log_info "Building Docker image..."
    docker build -t openpypi:latest . || log_warning "Docker build failed"
    
    # Security scan with trivy (if available)
    if command -v trivy &> /dev/null; then
        log_info "Running security scan with trivy..."
        trivy image openpypi:latest --format json --output trivy-report.json || log_warning "Trivy scan found vulnerabilities"
    fi
else
    log_warning "Docker not available, skipping Docker build"
fi

# 6. Generate Documentation
if command -v sphinx-build &> /dev/null; then
    log_info "Generating documentation..."
    cd docs && make html && cd .. || log_warning "Documentation generation failed"
else
    log_warning "Sphinx not available, skipping documentation generation"
fi

# 7. Generate Security Audit Report
log_info "Generating comprehensive security audit report..."
python -m openpypi.providers.audit --target openpypi:latest --output security-audit.sarif || log_warning "Security audit failed"

# 8. Package Analysis
log_info "Analyzing package..."
pip-audit || log_warning "pip-audit found vulnerabilities"

# 9. Performance Benchmarking
log_info "Running performance benchmarks..."
pytest tests/unit/providers/test_providers_enhanced.py::TestProviderPerformance \
    --benchmark-enable \
    --benchmark-json=benchmark-results.json \
    -v

# 10. Generate Comprehensive Report
log_info "Generating comprehensive build report..."
cat > build-report.md << EOF
# OpenPypi Build Report

Generated on: $(date)

## Test Results
- Unit tests: $(grep "passed" test-results.xml | wc -l || echo "N/A") passed
- Code coverage: $(grep -o 'line-rate="[^"]*"' coverage.xml | head -1 | cut -d'"' -f2 | awk '{print $1*100"%"}' || echo "N/A")

## Code Quality
- Black formatting: ✅ Applied
- isort imports: ✅ Sorted
- flake8 style: $(flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503 | wc -l) issues
- mypy types: $(mypy src/ --ignore-missing-imports 2>&1 | grep -c "error:" || echo "0") errors
- bandit security: $(jq '.results | length' security-report.json 2>/dev/null || echo "N/A") issues

## Package
- Wheel built: $(ls dist/*.whl | wc -l) files
- Source dist: $(ls dist/*.tar.gz | wc -l) files

## Security
- Trivy scan: $(jq '.Results[].Vulnerabilities | length' trivy-report.json 2>/dev/null || echo "N/A") vulnerabilities
- pip-audit: $(pip-audit --format=json 2>/dev/null | jq '.vulnerabilities | length' || echo "N/A") vulnerabilities

## Performance
- Benchmark results available in: benchmark-results.json

## Next Steps
1. Review any failed tests or quality issues
2. Address security vulnerabilities if found
3. Deploy to staging environment
4. Run end-to-end tests
5. Deploy to production

EOF

# Summary
log_success "Build and test process completed!"
log_info "Check build-report.md for detailed results"

# Check for critical failures
if [ -f "test-results.xml" ] && grep -q "failures=" test-results.xml; then
    FAILURES=$(grep -o 'failures="[^"]*"' test-results.xml | cut -d'"' -f2)
    if [ "$FAILURES" != "0" ]; then
        log_error "There were $FAILURES test failures!"
        exit 1
    fi
fi

log_success "All critical checks passed! ✅"

# Optional: Run stress tests if requested
if [ "$1" = "--stress" ]; then
    log_info "Running stress tests..."
    pytest tests/unit/providers/test_providers_enhanced.py -m "stress" -v --tb=short
fi

# Optional: Deploy if requested and tests pass
if [ "$1" = "--deploy" ] && [ -z "$FAILURES" ]; then
    log_info "Deploying to staging..."
    # Add deployment commands here
    echo "Deployment commands would go here"
fi 