"""
Stage 2: Architecture Design - Design the package structure and architecture.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class ArchitectStage(BaseStage):
    """
    Stage 2: Architecture Design

    This stage designs the technical architecture, module structure,
    and overall organization of the Python package.
    """

    async def execute(self, context: PackageContext) -> None:
        """Execute the architecture design stage."""
        self.log_stage_start()

        try:
            # Get previous stage output
            concept_data = context.get_stage_output("p1_concept")

            # Generate architecture design
            system_prompt = self.get_system_prompt()
            user_prompt = self.get_user_prompt(context)

            response = await self.provider.generate_response(
                prompt=user_prompt, system_prompt=system_prompt, temperature=0.6
            )

            # Parse and validate response
            architecture_data = await self._parse_architecture_response(response["content"], context)

            if await self.validate_output(architecture_data):
                # Update context with architecture
                context.dependencies.extend(architecture_data.get("dependencies", []))
                context.dev_dependencies.extend(architecture_data.get("dev_dependencies", []))

                # Store stage output
                context.set_stage_output("p2_architecture", architecture_data)

                # Create directory structure
                await self._create_directory_structure(context, architecture_data)

                self.log_stage_end()
            else:
                raise ValueError("Invalid architecture output generated")

        except Exception as e:
            self.log_stage_error(e)
            raise

    def get_system_prompt(self) -> str:
        """Get the system prompt for architecture design."""
        return """You are a senior Python software architect with expertise in designing scalable, maintainable package architectures. You excel at:

        - Designing clean, modular architectures following SOLID principles
        - Selecting appropriate design patterns for Python packages
        - Organizing code for maximum maintainability and testability
        - Following Python packaging best practices (PEP 517, PEP 621)
        - Choosing optimal dependencies and avoiding dependency hell
        - Designing APIs that are intuitive and Pythonic
        - Planning for extensibility and future growth

        Always consider:
        - Modern Python packaging standards
        - Type safety and static analysis
        - Testing strategies and test organization
        - Documentation structure
        - CI/CD pipeline requirements
        - Security best practices
        - Performance considerations

        Respond with detailed JSON that includes complete module structure, dependencies, and architectural decisions.
        """

    def get_user_prompt(self, context: PackageContext) -> str:
        """Get the user prompt for architecture design."""
        concept_data = context.get_stage_output("p1_concept") or {}

        return f"""Design a comprehensive architecture for the following Python package:

        **Package Name:** {context.package_name}
        **Package Type:** {context.package_type}
        **Python Version:** {context.python_version}

        **Concept Summary:**
        - Description: {concept_data.get('refined_description', context.idea)}
        - Key Features: {', '.join(concept_data.get('key_features', []))}
        - Complexity Level: {concept_data.get('technical_considerations', {}).get('complexity_level', 'medium')}
        - Async Support: {concept_data.get('technical_considerations', {}).get('async_support', False)}

        **Requirements:**
        - Features: {', '.join(context.features)}
        - Constraints: {', '.join(context.constraints)}

        Please provide a complete architecture design in the following JSON format:

        {{
            "package_structure": {{
                "src/{context.package_name}/": {{
                    "__init__.py": "Package initialization and public API",
                    "core/": {{
                        "__init__.py": "Core module initialization",
                        "main.py": "Main functionality implementation",
                        "exceptions.py": "Custom exception classes",
                        "types.py": "Type definitions and protocols"
                    }},
                    "utils/": {{
                        "__init__.py": "Utilities initialization",
                        "helpers.py": "Helper functions",
                        "validators.py": "Validation utilities"
                    }},
                    "cli/": {{
                        "__init__.py": "CLI module initialization",
                        "main.py": "Command-line interface"
                    }}
                }},
                "tests/": {{
                    "__init__.py": "Test package initialization",
                    "unit/": {{}},
                    "integration/": {{}},
                    "fixtures/": {{}}
                }},
                "docs/": {{
                    "source/": {{}},
                    "examples/": {{}}
                }}
            }},
            "dependencies": {{
                "core": ["dependency1>=1.0.0", "dependency2>=2.0.0"],
                "optional": {{
                    "cli": ["click>=8.0.0"],
                    "async": ["aiohttp>=3.8.0"],
                    "dev": ["pytest>=7.0.0", "black>=22.0.0"]
                }}
            }},
            "api_design": {{
                "public_classes": [
                    {{
                        "name": "ClassName",
                        "purpose": "What this class does",
                        "methods": ["method1", "method2"],
                        "properties": ["prop1", "prop2"]
                    }}
                ],
                "public_functions": [
                    {{
                        "name": "function_name",
                        "purpose": "What this function does",
                        "parameters": ["param1: type", "param2: type"],
                        "returns": "return_type"
                    }}
                ],
                "entry_points": {{
                    "console_scripts": ["command_name = package.module:function"],
                    "api_endpoints": []
                }}
            }},
            "design_patterns": [
                {{
                    "pattern": "Pattern Name",
                    "usage": "Where and why it's used",
                    "implementation": "Brief implementation notes"
                }}
            ],
            "configuration": {{
                "config_files": ["config.yaml", "settings.toml"],
                "environment_variables": ["VAR_NAME", "ANOTHER_VAR"],
                "default_settings": {{}}
            }},
            "testing_strategy": {{
                "unit_tests": "Strategy for unit testing",
                "integration_tests": "Strategy for integration testing",
                "test_fixtures": ["fixture1", "fixture2"],
                "coverage_target": 90
            }},
            "documentation_plan": {{
                "api_docs": "Sphinx with autodoc",
                "user_guide": "Getting started and tutorials",
                "examples": ["example1.py", "example2.py"],
                "changelog": "Keep a changelog format"
            }},
            "quality_assurance": {{
                "linting": ["flake8", "pylint"],
                "formatting": ["black", "isort"],
                "type_checking": "mypy",
                "security": ["bandit", "safety"]
            }},
            "architectural_decisions": [
                {{
                    "decision": "Decision made",
                    "rationale": "Why this decision was made",
                    "alternatives": "Other options considered",
                    "consequences": "Impact of this decision"
                }}
            ]
        }}

        Ensure the architecture:
        1. Follows modern Python packaging standards (PEP 517, PEP 621)
        2. Is modular and extensible
        3. Supports the required features and constraints
        4. Includes proper error handling and logging
        5. Has a clear separation of concerns
        6. Is testable and maintainable
        7. Follows Python naming conventions and best practices
        """

    async def _parse_architecture_response(self, response_content: str, context: PackageContext) -> Dict[str, Any]:
        """Parse the architecture response from the AI."""
        try:
            architecture_data = json.loads(response_content)
            return architecture_data
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, using fallback extraction")

            # Fallback architecture
            architecture_data = {
                "package_structure": {
                    f"src/{context.package_name}/": {
                        "__init__.py": "Package initialization",
                        "core.py": "Core functionality",
                        "utils.py": "Utility functions",
                        "exceptions.py": "Custom exceptions",
                    },
                    "tests/": {"test_core.py": "Core tests", "test_utils.py": "Utility tests"},
                },
                "dependencies": {"core": [], "optional": {"dev": ["pytest>=7.0.0"]}},
                "api_design": {
                    "public_classes": [],
                    "public_functions": [],
                    "entry_points": {"console_scripts": []},
                },
            }

            return architecture_data

    async def _create_directory_structure(
        self, context: PackageContext, architecture_data: Dict[str, Any]
    ) -> None:
        """Create the directory structure based on architecture design."""
        package_structure = architecture_data.get("package_structure", {})

        def create_structure(base_path: Path, structure: Dict[str, Any]) -> None:
            for name, content in structure.items():
                path = base_path / name

                if isinstance(content, dict):
                    # It's a directory
                    path.mkdir(parents=True, exist_ok=True)
                    create_structure(path, content)
                else:
                    # It's a file
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not path.exists():
                        # Create empty file with comment
                        path.write_text(f'"""{content}"""\n')

        create_structure(context.output_dir, package_structure)
        logger.info(f"Created directory structure in {context.output_dir}")

    async def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate the architecture output."""
        required_fields = ["package_structure", "dependencies", "api_design"]

        for field in required_fields:
            if field not in output:
                logger.error(f"Missing required field in architecture output: {field}")
                return False

        # Validate package structure
        package_structure = output.get("package_structure", {})
        if not package_structure:
            logger.error("Package structure cannot be empty")
            return False

        return True
