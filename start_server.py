#!/usr/bin/env python3
"""
OpenPypi Development Server Startup Script
Automatically handles port conflicts and environment setup
"""

import os
import socket
import subprocess
import sys
from pathlib import Path


def find_available_port(start_port: int = 8002) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("localhost", port))
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
    print(f"Starting OpenPypi server on port {port}")

    # Set environment variables
    os.environ["API_PORT"] = str(port)
    os.environ["PYTHONPATH"] = str(project_root / "src")

    # Start server
    try:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "openpypi.api.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--reload",
        ]

        print(f"Server will be available at: http://localhost:{port}")
        print(f"API docs will be available at: http://localhost:{port}/docs")
        print("Press Ctrl+C to stop the server")

        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
