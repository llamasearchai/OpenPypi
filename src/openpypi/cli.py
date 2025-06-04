"""
Command-line interface for OpenPypi.

This module provides the main CLI entry point for OpenPypi, supporting:
- Project generation with customizable templates
- FastAPI server management
- Provider management and testing
- Configuration validation
- Package publishing to PyPI
"""

import argparse
import asyncio
import importlib.metadata
import os
import sys
from pathlib import Path
from typing import List, Optional

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False

from .core import Config, ProjectGenerator
from .core.context import PackageContext
from .core.exceptions import OpenPypiException
from .providers import get_provider, list_providers
from .utils.logger import get_logger, setup_logging
from .stages.p6_deployer import DeployerStage

logger = get_logger(__name__)


def get_version() -> str:
    """Get package version."""
    try:
        return importlib.metadata.version("openpypi")
    except importlib.metadata.PackageNotFoundError:
        return "1.0.0"


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="OpenPypi - Complete Python Project Generator",
        prog="openpypi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  openpypi create my_project --author "Nik Jois" --email "nikjois@llamasearch.ai"
  openpypi create my_api --use-fastapi --use-docker --use-openai
  openpypi serve --host 0.0.0.0 --port 8000 --reload
  openpypi validate config.toml
  openpypi providers list
  openpypi publish ./my_project --token $PYPI_TOKEN
        """,
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {get_version()}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--config", "-c", type=str, help="Path to configuration file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command (alias for generate)
    create_parser = subparsers.add_parser("create", help="Create a new project")
    _add_generate_arguments(create_parser)

    # Generate command (legacy)
    generate_parser = subparsers.add_parser("generate", help="Generate a new project")
    _add_generate_arguments(generate_parser)

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    serve_parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    serve_parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug"],
        help="Log level",
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument("config_file", nargs="?", help="Configuration file to validate")

    # Providers command
    providers_parser = subparsers.add_parser("providers", help="Manage providers")
    providers_subparsers = providers_parser.add_subparsers(dest="providers_action")

    # List providers
    providers_subparsers.add_parser("list", help="List available providers")

    # Test provider
    test_provider_parser = providers_subparsers.add_parser("test", help="Test provider connection")
    test_provider_parser.add_argument("provider_name", help="Provider name to test")
    test_provider_parser.add_argument("--config-key", help="Configuration key for provider")

    # Provider capabilities
    caps_parser = providers_subparsers.add_parser("capabilities", help="Show provider capabilities")
    caps_parser.add_argument("provider_name", help="Provider name")

    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="config_action")

    # Show config
    config_subparsers.add_parser("show", help="Show current configuration")

    # Create config template
    create_config_parser = config_subparsers.add_parser(
        "create", help="Create configuration template"
    )
    create_config_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("openpypi.toml"),
        help="Output file for configuration template",
    )
    create_config_parser.add_argument(
        "--format", choices=["toml", "json"], default="toml", help="Configuration file format"
    )

    # Publish command
    publish_parser = subparsers.add_parser("publish", help="Publish package to PyPI")
    publish_parser.add_argument("project_dir", type=Path, help="Path to project directory")
    publish_parser.add_argument("--token", help="PyPI API token (or use PYPI_TOKEN env var)")
    publish_parser.add_argument("--repository-url", default="https://upload.pypi.org/legacy/",
                              help="PyPI repository URL")
    publish_parser.add_argument("--skip-build", action="store_true", 
                              help="Skip building distributions")
    publish_parser.add_argument("--test", action="store_true",
                              help="Upload to test.pypi.org instead")

    return parser


def _add_generate_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for generate/create commands."""
    parser.add_argument("project_name", help="Name of the project to create")
    parser.add_argument(
        "--package-name", help="Package name (defaults to project name with underscores)"
    )
    parser.add_argument("--author", default="Developer", help="Author name")
    parser.add_argument("--email", default="nikjois@llamasearch.ai", help="Author email")
    parser.add_argument("--description", help="Project description")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)",
    )

    # Feature flags
    parser.add_argument("--use-fastapi", action="store_true", help="Enable FastAPI integration")
    parser.add_argument("--use-openai", action="store_true", help="Enable OpenAI integration")
    parser.add_argument("--use-docker", action="store_true", help="Enable Docker support")
    parser.add_argument("--use-github-actions", action="store_true", help="Enable GitHub Actions")
    parser.add_argument("--create-tests", action="store_true", help="Generate test files")
    parser.add_argument("--use-git", action="store_true", help="Initialize git repository")

    # Disable flags (for backward compatibility)
    parser.add_argument("--no-fastapi", action="store_true", help="Disable FastAPI integration")
    parser.add_argument("--no-openai", action="store_true", help="Disable OpenAI integration")
    parser.add_argument("--no-docker", action="store_true", help="Disable Docker support")
    parser.add_argument("--no-tests", action="store_true", help="Disable test generation")
    parser.add_argument("--no-git", action="store_true", help="Skip git initialization")

    parser.add_argument(
        "--test-framework",
        choices=["pytest", "unittest"],
        default="pytest",
        help="Test framework to use",
    )
    parser.add_argument("--license", default="MIT", help="License type")
    parser.add_argument("--python-requires", default=">=3.8", help="Python version requirement")


def handle_create_command(args) -> int:
    """Handle the create/generate command."""
    try:
        # Load base configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config()

        # Override with command line arguments
        config.project_name = args.project_name
        config.package_name = args.package_name or args.project_name.replace("-", "_").lower()
        config.author = args.author
        config.email = args.email
        config.output_dir = args.output_dir
        config.license = args.license
        config.python_requires = args.python_requires

        if args.description:
            config.description = args.description
        else:
            config.description = f"A Python package for {config.project_name}"

        # Handle feature flags (use explicit enables first, then disable flags)
        if args.use_fastapi:
            config.use_fastapi = True
        elif args.no_fastapi:
            config.use_fastapi = False

        if args.use_openai:
            config.use_openai = True
        elif args.no_openai:
            config.use_openai = False

        if args.use_docker:
            config.use_docker = True
        elif args.no_docker:
            config.use_docker = False

        if args.create_tests:
            config.create_tests = True
        elif args.no_tests:
            config.create_tests = False

        if args.use_git:
            config.use_git = True
        elif args.no_git:
            config.use_git = False

        if args.use_github_actions:
            config.use_github_actions = True

        config.test_framework = args.test_framework

        # Validate configuration
        config.validate()

        logger.info(f"Creating project '{config.project_name}' in {config.output_dir}")

        # Generate project
        generator = ProjectGenerator(config)
        results = generator.generate()

        # Print results
        print(f"\nProject '{config.project_name}' created successfully!")
        print(f"Location: {results['project_dir']}")
        print(f"Files created: {len(results['files_created'])}")
        print(f"Directories created: {len(results['directories_created'])}")

        if results.get("commands_run"):
            print(f"Commands executed: {len(results['commands_run'])}")

        if results.get("warnings"):
            print(f"\nWarnings:")
            for warning in results["warnings"]:
                print(f"   • {warning}")

        # Display next steps
        print(f"\nNext steps:")
        project_path = Path(results["project_dir"])
        print(f"   cd {project_path.name}")

        if config.use_fastapi:
            print(f"   # Install dependencies")
            print(f"   pip install -e .[dev]")
            print(f"   # Start FastAPI server")
            print(f"   uvicorn {config.package_name}.api:app --reload")

        if config.use_docker:
            print(f"   # Build Docker image")
            print(f"   docker build -t {config.package_name} .")
            print(f"   # Run with docker-compose")
            print(f"   docker-compose up")

        if config.create_tests:
            print(f"   # Run tests")
            print(f"   pytest")
            print(f"   # Run tests with coverage")
            print(f"   pytest --cov={config.package_name}")

        print(f"\n   # Publish to PyPI")
        print(f"   openpypi publish . --token YOUR_PYPI_TOKEN")

        return 0

    except OpenPypiException as e:
        logger.error(f"Creation failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_serve_command(args) -> int:
    """Handle the serve command."""
    try:
        if not UVICORN_AVAILABLE:
            print("Error: uvicorn is required for the serve command", file=sys.stderr)
            print("   Install with: pip install 'openpypi[dev]'", file=sys.stderr)
            return 1

        # Import the FastAPI app
        from .api import create_app

        app = create_app()

        print(f"Starting OpenPypi API server...")
        print(f"   Host: {args.host}")
        print(f"   Port: {args.port}")
        print(f"   Reload: {args.reload}")
        print(f"   Workers: {args.workers}")
        print(f"   Log level: {args.log_level}")
        print(f"   Docs: http://{args.host}:{args.port}/docs")

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level=args.log_level,
        )

        return 0

    except ImportError as e:
        logger.error(f"Failed to import FastAPI app: {e}")
        print(f"Error: Failed to start server - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"Server error: {e}", file=sys.stderr)
        return 1


def handle_validate_command(args) -> int:
    """Handle the validate command."""
    try:
        config_file = args.config_file or args.config

        if not config_file:
            # Look for default config files
            default_files = ["openpypi.toml", "openpypi.json", ".openpypi.toml", ".openpypi.json"]
            for filename in default_files:
                if Path(filename).exists():
                    config_file = filename
                    break

            if not config_file:
                print("No configuration file specified or found", file=sys.stderr)
                print("   Use: openpypi validate <config_file>", file=sys.stderr)
                return 1

        print(f"Validating configuration: {config_file}")

        # Load and validate configuration
        config = Config.from_file(config_file)
        config.validate()

        print("Configuration is valid!")

        # Show configuration summary
        print(f"\nConfiguration Summary:")
        print(f"  Project: {config.project_name}")
        print(f"  Package: {config.package_name}")
        print(f"  Author: {config.author} <{config.email}>")
        print(f"  Version: {config.version}")
        print(f"  Python: {config.python_requires}")
        print(
            f"  Features: FastAPI={config.use_fastapi}, Docker={config.use_docker}, OpenAI={config.use_openai}"
        )

        return 0

    except OpenPypiException as e:
        print(f"Configuration invalid: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Validation error: {e}")
        print(f"Validation error: {e}", file=sys.stderr)
        return 1


def handle_providers_command(args) -> int:
    """Handle the providers command."""
    try:
        if args.providers_action == "list":
            providers = list_providers()
            print("Available Providers:")
            print("===================")
            for provider_name in providers:
                try:
                    provider = get_provider(provider_name)
                    capabilities = provider.get_capabilities()
                    status = "Available" if provider.is_configured else "Not configured"
                    print(f"{provider_name:15} {status:15} {', '.join(capabilities)}")
                except Exception as e:
                    print(f"{provider_name:15} {'Error':15} {e}")

        elif args.providers_action == "test":
            provider_name = args.provider_name
            print(f"Testing provider: {provider_name}")

            config = {}
            if args.config_key:
                config_value = os.getenv(args.config_key)
                if config_value:
                    config[args.config_key.lower()] = config_value

            provider = get_provider(provider_name, config)

            if provider.validate_connection():
                print(f"Provider '{provider_name}' connection successful!")
            else:
                print(f"Provider '{provider_name}' connection failed!")
                return 1

        elif args.providers_action == "capabilities":
            provider_name = args.provider_name
            provider = get_provider(provider_name)
            capabilities = provider.get_capabilities()

            print(f"Provider Capabilities: {provider_name}")
            print("=" * (len(provider_name) + 22))
            for capability in capabilities:
                print(f"  • {capability}")

        return 0

    except Exception as e:
        logger.error(f"Provider command error: {e}")
        print(f"Provider error: {e}", file=sys.stderr)
        return 1


def handle_config_command(args) -> int:
    """Handle the config command."""
    try:
        if args.config_action == "show":
            # Show current configuration
            config_file = args.config
            if config_file:
                config = Config.from_file(config_file)
                print(f"Configuration from: {config_file}")
            else:
                config = Config.from_env()
                print("Configuration from environment/defaults:")

            print("=" * 40)
            config_dict = config.to_dict()
            for key, value in config_dict.items():
                print(f"{key:20}: {value}")

        elif args.config_action == "create":
            # Create configuration template
            config = Config()

            if args.format == "json":
                output_file = args.output.with_suffix(".json")
            else:
                output_file = args.output

            config.to_file(output_file)
            print(f"Configuration template created: {output_file}")
            print(
                f"   Edit the file and use with: openpypi create my_project --config {output_file}"
            )

        return 0

    except OpenPypiException as e:
        logger.error(f"Config operation failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_publish_command(args) -> int:
    """
    Handle the publish command to upload packages to PyPI.
    
    This command:
    1. Builds the package distributions if not already built
    2. Validates the distributions
    3. Uploads to PyPI using the provided token
    """
    try:
        import subprocess
        from pathlib import Path
        
        project_dir = args.project_dir.resolve()
        
        # Check if project directory exists
        if not project_dir.exists():
            print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
            return 1
            
        # Get PyPI token
        pypi_token = args.token or os.getenv("PYPI_TOKEN")
        if not pypi_token:
            print("Error: PyPI token not provided. Use --token or set PYPI_TOKEN env var", file=sys.stderr)
            return 1
            
        # Set repository URL
        if args.test:
            repository_url = "https://test.pypi.org/legacy/"
        else:
            repository_url = args.repository_url
            
        # Build distributions if needed
        dist_dir = project_dir / "dist"
        if not args.skip_build or not dist_dir.exists() or not list(dist_dir.glob("*.tar.gz")):
            print(f"Building distributions in {project_dir}...")
            
            # Clean old distributions
            if dist_dir.exists():
                import shutil
                shutil.rmtree(dist_dir)
                
            # Build the package
            result = subprocess.run(
                [sys.executable, "-m", "build", "--outdir", str(dist_dir)],
                cwd=project_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Build failed: {result.stderr}", file=sys.stderr)
                return 1
                
            print("Build successful!")
            
        # Check for distribution files
        dist_files = list(dist_dir.glob("*.tar.gz")) + list(dist_dir.glob("*.whl"))
        if not dist_files:
            print("Error: No distribution files found to upload", file=sys.stderr)
            return 1
            
        print(f"Found {len(dist_files)} distribution files to upload")
        
        # Upload using twine
        print(f"Uploading to {repository_url}...")
        
        # Create the upload command
        upload_cmd = [
            sys.executable, "-m", "twine", "upload",
            "--repository-url", repository_url,
            "--username", "__token__",
            "--password", pypi_token,
            "--verbose"
        ]
        
        # Add all distribution files
        upload_cmd.extend(str(f) for f in dist_files)
        
        # Run upload
        result = subprocess.run(upload_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\nPackage published successfully!")
            if args.test:
                print(f"View at: https://test.pypi.org/project/{project_dir.name}/")
            else:
                print(f"View at: https://pypi.org/project/{project_dir.name}/")
            return 0
        else:
            print(f"Upload failed: {result.stderr}", file=sys.stderr)
            return 1
            
    except Exception as e:
        logger.error(f"Publish error: {e}")
        print(f"Publish error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.
    
    This function:
    1. Parses command-line arguments
    2. Sets up logging based on verbosity
    3. Routes to appropriate command handlers
    4. Returns exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)

    # Handle commands
    if args.command in ("create", "generate"):
        return handle_create_command(args)
    elif args.command == "serve":
        return handle_serve_command(args)
    elif args.command == "validate":
        return handle_validate_command(args)
    elif args.command == "providers":
        return handle_providers_command(args)
    elif args.command == "config":
        return handle_config_command(args)
    elif args.command == "publish":
        return handle_publish_command(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
