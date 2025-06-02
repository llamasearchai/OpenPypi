"""
Command-line interface for OpenPypi.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .core import Config, ProjectGenerator
from .core.exceptions import OpenPypiError
from .utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="OpenPypi - Complete Python Project Generator",
        prog="openpypi"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s 0.1.0"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a new project")
    generate_parser.add_argument(
        "project_name",
        help="Name of the project to generate"
    )
    generate_parser.add_argument(
        "--package-name",
        help="Package name (defaults to project name with underscores)"
    )
    generate_parser.add_argument(
        "--author",
        default="Developer",
        help="Author name"
    )
    generate_parser.add_argument(
        "--email",
        default="developer@example.com",
        help="Author email"
    )
    generate_parser.add_argument(
        "--description",
        help="Project description"
    )
    generate_parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)"
    )
    generate_parser.add_argument(
        "--no-fastapi",
        action="store_true",
        help="Disable FastAPI integration"
    )
    generate_parser.add_argument(
        "--no-openai",
        action="store_true", 
        help="Disable OpenAI integration"
    )
    generate_parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Disable Docker support"
    )
    generate_parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Disable test generation"
    )
    generate_parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git initialization"
    )
    generate_parser.add_argument(
        "--test-framework",
        choices=["pytest", "unittest"],
        default="pytest",
        help="Test framework to use"
    )
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    
    # Show config
    config_subparsers.add_parser("show", help="Show current configuration")
    
    # Create config template
    create_config_parser = config_subparsers.add_parser("create", help="Create configuration template")
    create_config_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("openpypi.toml"),
        help="Output file for configuration template"
    )
    
    return parser


def handle_generate_command(args) -> int:
    """Handle the generate command."""
    try:
        # Load base configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config()
        
        # Override with command line arguments
        config.project_name = args.project_name
        config.package_name = args.package_name or args.project_name.replace('-', '_').lower()
        config.author = args.author
        config.email = args.email
        config.output_dir = args.output_dir
        
        if args.description:
            config.description = args.description
        else:
            config.description = f"A Python package for {config.project_name}"
        
        # Handle feature flags
        config.use_fastapi = not args.no_fastapi
        config.use_openai = not args.no_openai
        config.use_docker = not args.no_docker
        config.create_tests = not args.no_tests
        config.use_git = not args.no_git
        config.test_framework = args.test_framework
        
        # Validate configuration
        config.validate()
        
        logger.info(f"Generating project '{config.project_name}' in {config.output_dir}")
        
        # Generate project
        generator = ProjectGenerator(config)
        results = generator.generate()
        
        # Print results
        print(f"\n✅ Project '{config.project_name}' generated successfully!")
        print(f"📁 Location: {results['project_dir']}")
        print(f"📄 Files created: {len(results['files_created'])}")
        print(f"📁 Directories created: {len(results['directories_created'])}")
        
        if results['commands_run']:
            print(f"🔧 Commands executed: {len(results['commands_run'])}")
        
        if results['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in results['warnings']:
                print(f"   • {warning}")
        
        print(f"\n🚀 Next steps:")
        print(f"   cd {Path(results['project_dir']).name}")
        if config.use_fastapi:
            print(f"   uvicorn {config.package_name}.api.app:app --reload")
        else:
            print(f"   {config.package_name} run")
        
        return 0
        
    except OpenPypiError as e:
        logger.error(f"Generation failed: {e}")
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_config_command(args) -> int:
    """Handle the config command."""
    try:
        if args.config_action == "show":
            # Show current configuration
            config = Config()
            if args.config:
                config = Config.from_file(args.config)
            
            print("Current Configuration:")
            print("=====================")
            config_dict = config.to_dict()
            for key, value in config_dict.items():
                print(f"{key}: {value}")
            
        elif args.config_action == "create":
            # Create configuration template
            config = Config()
            config.to_file(args.output)
            print(f"✅ Configuration template created: {args.output}")
            
        return 0
        
    except OpenPypiError as e:
        logger.error(f"Config operation failed: {e}")
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    # Handle commands
    if args.command == "generate":
        return handle_generate_command(args)
    elif args.command == "config":
        return handle_config_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 