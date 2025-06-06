#!/usr/bin/env python3
"""
Environment Configuration Fix Script
Fixes .env file formatting and port binding issues
"""

import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def find_available_port(start_port: int = 8001, max_port: int = 8100) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("localhost", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")


def kill_processes_on_port(port: int) -> bool:
    """Kill processes running on the specified port."""
    try:
        if sys.platform == "darwin":  # macOS
            result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    subprocess.run(["kill", "-9", pid], check=False)
                print(f"Killed processes on port {port}")
                return True
        elif sys.platform == "linux":
            result = subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, text=True)
            print(f"Killed processes on port {port}")
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return False


def create_env_file(project_root: Path) -> None:
    """Create a properly formatted .env file."""
    env_content = """# OpenPypi Environment Configuration
# Development Environment Settings

APP_NAME=OpenPypi
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here-change-in-production

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/openpypi_dev
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/openpypi_test

REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

API_HOST=0.0.0.0
API_PORT={available_port}
API_WORKERS=4
API_RELOAD=true

CORS_ORIGINS=["http://localhost:3000", "http://localhost:{available_port}", "http://127.0.0.1:{available_port}"]
ALLOWED_HOSTS=["localhost", "127.0.0.1", "0.0.0.0"]

JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=10080

OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7

PYPI_API_TOKEN=your-pypi-api-token-here
TEST_PYPI_API_TOKEN=your-test-pypi-api-token-here

DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=openpypi
DOCKER_TAG=latest

GITHUB_TOKEN=your-github-token-here
GITHUB_WEBHOOK_SECRET=your-github-webhook-secret

SLACK_WEBHOOK_URL=your-slack-webhook-url-here
SLACK_BOT_TOKEN=your-slack-bot-token-here

LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=your-sentry-dsn-here

MAX_WORKERS=4
WORKER_TIMEOUT=300
KEEPALIVE_TIMEOUT=5

MAX_FILE_SIZE=100MB
UPLOAD_FOLDER=/tmp/uploads
ALLOWED_EXTENSIONS=.py,.txt,.md,.yml,.yaml,.json,.toml

CACHE_TYPE=redis
CACHE_DEFAULT_TIMEOUT=300
CACHE_KEY_PREFIX=openpypi:

ENABLE_PROFILER=false
ENABLE_DEBUG_TOOLBAR=false
AUTO_RELOAD=true

TEST_PARALLEL=true
TEST_COVERAGE_THRESHOLD=80
TEST_TIMEOUT=300

SECURITY_SCAN_ENABLED=true
VULNERABILITY_DB_UPDATE_INTERVAL=86400

DEFAULT_PYTHON_VERSION=3.11
DEFAULT_PACKAGE_TEMPLATE=fastapi
ENABLE_AI_SUGGESTIONS=true
"""

    # Find available port
    available_port = find_available_port()
    env_content = env_content.format(available_port=available_port)

    env_file = project_root / ".env"
    env_example_file = project_root / ".env.example"

    # Create .env.example
    with open(env_example_file, "w") as f:
        f.write(env_content)
    print(f"Created {env_example_file}")

    # Create .env if it doesn't exist or has issues
    if not env_file.exists() or has_env_formatting_issues(env_file):
        with open(env_file, "w") as f:
            f.write(env_content)
        print(f"Created/Fixed {env_file} with port {available_port}")

    return available_port


def has_env_formatting_issues(env_file: Path) -> bool:
    """Check if .env file has formatting issues."""
    try:
        with open(env_file, "r") as f:
            content = f.read()

        # Check for common issues
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                print(f"Line {line_num}: Missing '=' in '{line}'")
                return True

            key, value = line.split("=", 1)

            # Check for spaces in key
            if " " in key:
                print(f"Line {line_num}: Key contains spaces: '{key}'")
                return True

        return False
    except Exception as e:
        print(f"Error reading .env file: {e}")
        return True


def fix_docker_compose(project_root: Path, port: int) -> None:
    """Fix docker-compose.yml to use the correct port."""
    docker_compose_file = project_root / "docker-compose.yml"

    if docker_compose_file.exists():
        try:
            with open(docker_compose_file, "r") as f:
                content = f.read()

            # Replace port references
            content = content.replace("8000:8000", f"{port}:8000")
            content = content.replace('- "8000:', f'- "{port}:')

            with open(docker_compose_file, "w") as f:
                f.write(content)

            print(f"Updated docker-compose.yml to use port {port}")
        except Exception as e:
            print(f"Could not update docker-compose.yml: {e}")


def create_startup_script(project_root: Path, port: int) -> None:
    """Create a startup script that handles port conflicts."""
    startup_script = project_root / "start_server.py"

    script_content = f'''#!/usr/bin/env python3
"""
OpenPypi Development Server Startup Script
Automatically handles port conflicts and environment setup
"""

import os
import sys
import subprocess
import socket
from pathlib import Path

def find_available_port(start_port: int = {port}) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available ports found")

def main():
    """Start the OpenPypi server."""
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Find available port
    port = find_available_port()
    print(f"Starting OpenPypi server on port {{port}}")
    
    # Set environment variables
    os.environ['API_PORT'] = str(port)
    os.environ['PYTHONPATH'] = str(project_root / 'src')
    
    # Start server
    try:
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'openpypi.api.app:app',
            '--host', '0.0.0.0',
            '--port', str(port),
            '--reload'
        ]
        
        print(f"Server will be available at: http://localhost:{{port}}")
        print(f"API docs will be available at: http://localhost:{{port}}/docs")
        print("Press Ctrl+C to stop the server")
        
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\\nServer stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

    with open(startup_script, "w") as f:
        f.write(script_content)

    # Make executable
    os.chmod(startup_script, 0o755)
    print(f"Created startup script: {startup_script}")


def main():
    """Fix environment configuration issues."""
    print("OpenPypi Environment Fix Script")
    print("=" * 40)

    project_root = Path.cwd()

    # Kill processes on default port 8000
    print("Checking for processes on port 8000...")
    kill_processes_on_port(8000)

    # Create/fix .env file
    print("Creating/fixing environment configuration...")
    available_port = create_env_file(project_root)

    # Fix docker-compose
    print("Updating Docker configuration...")
    fix_docker_compose(project_root, available_port)

    # Create startup script
    print("Creating startup script...")
    create_startup_script(project_root, available_port)

    print("\n" + "=" * 40)
    print("Environment fix completed!")
    print(f"Server configured to use port: {available_port}")
    print("\nNext steps:")
    print("1. Run: python start_server.py")
    print("2. Or run: uvicorn openpypi.api.app:app --reload --port " + str(available_port))
    print(f"3. Access the application at: http://localhost:{available_port}")
    print(f"4. View API docs at: http://localhost:{available_port}/docs")

    # Check if .env needs manual review
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"\nPlease review {env_file} and update:")
        print("   - API keys (OpenAI, PyPI, GitHub, etc.)")
        print("   - Database credentials")
        print("   - Secret keys")
        print("   - Webhook URLs")


if __name__ == "__main__":
    main()
