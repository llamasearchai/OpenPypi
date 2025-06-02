"""
Stage 5: Documentation - Generate comprehensive documentation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentarianStage(BaseStage):
    """
    Stage 5: Documentation
    
    This stage generates comprehensive documentation including README,
    API documentation, user guides, and examples.
    """
    
    async def execute(self, context: PackageContext) -> None:
        """Execute the documentation stage."""
        self.log_stage_start()
        
        try:
            # Get previous stage outputs
            concept_data = context.get_stage_output("p1_concept") or {}
            architecture_data = context.get_stage_output("p2_architecture") or {}
            implementation_data = context.get_stage_output("p3_implementation") or {}
            
            # Generate documentation
            docs_data = await self._generate_documentation(
                context, concept_data, architecture_data, implementation_data
            )
            
            if await self.validate_output(docs_data):
                # Write documentation files
                await self._write_documentation_files(context, docs_data)
                
                # Generate Sphinx configuration
                await self._generate_sphinx_config(context, docs_data)
                
                # Generate examples
                await self._generate_examples(context, concept_data)
                
                # Store stage output
                context.set_stage_output("p5_documentation", docs_data)
                
                self.log_stage_end()
            else:
                raise ValueError("Invalid documentation output generated")
                
        except Exception as e:
            self.log_stage_error(e)
            raise
    
    async def _generate_documentation(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
        implementation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate all documentation content."""
        docs_data = {}
        
        # Generate README
        docs_data["README.md"] = await self._generate_readme(
            context, concept_data, architecture_data
        )
        
        # Generate API documentation
        docs_data["api_docs"] = await self._generate_api_docs(
            context, implementation_data
        )
        
        # Generate user guide
        docs_data["user_guide"] = await self._generate_user_guide(
            context, concept_data
        )
        
        # Generate changelog
        docs_data["CHANGELOG.md"] = await self._generate_changelog(context)
        
        # Generate contributing guide
        docs_data["CONTRIBUTING.md"] = await self._generate_contributing_guide(context)
        
        # Generate license
        docs_data["LICENSE"] = await self._generate_license(context)
        
        return docs_data
    
    async def _generate_readme(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any]
    ) -> str:
        """Generate README.md content."""
        system_prompt = self._get_readme_system_prompt()
        user_prompt = self._get_readme_user_prompt(context, concept_data, architecture_data)
        
        response = await self.provider.generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.6
        )
        
        return response["content"]
    
    def _get_readme_system_prompt(self) -> str:
        """Get system prompt for README generation."""
        return """You are an expert technical writer who creates compelling, comprehensive README files for Python packages. You excel at:

        - Writing clear, engaging introductions that immediately convey value
        - Creating well-structured documentation with logical flow
        - Including practical examples that demonstrate real usage
        - Adding appropriate badges and visual elements
        - Following README best practices and conventions
        - Making documentation accessible to different skill levels
        - Including all necessary sections for a professional package

        Always create README files that:
        1. Start with a compelling description and value proposition
        2. Include installation instructions
        3. Provide quick start examples
        4. Document the main features and API
        5. Include badges for build status, coverage, etc.
        6. Have clear contributing guidelines
        7. Include license information
        8. Are well-formatted with proper Markdown
        9. Include links to additional documentation
        10. Have a professional, polished appearance

        Generate complete, production-ready README content in Markdown format.
        """
    
    def _get_readme_user_prompt(
        self,
        context: PackageContext,
        concept_data: Dict[str, Any],
        architecture_data: Dict[str, Any]
    ) -> str:
        """Get user prompt for README generation."""
        features = concept_data.get('key_features', [])
        use_cases = concept_data.get('use_cases', [])
        api_design = architecture_data.get('api_design', {})
        
        return f"""Generate a comprehensive README.md for the Python package:

        **Package Information:**
        - Name: {context.package_name}
        - Version: {context.version}
        - Description: {concept_data.get('refined_description', context.idea)}
        - Author: {context.author}
        - License: {context.license_type}
        - Python Version: {context.python_version}

        **Key Features:**
        {chr(10).join(f"- {feature}" for feature in features)}

        **Use Cases:**
        {chr(10).join(f"- {use_case}" for use_case in use_cases)}

        **API Overview:**
        - Classes: {len(api_design.get('public_classes', []))}
        - Functions: {len(api_design.get('public_functions', []))}
        - Entry Points: {api_design.get('entry_points', {})}

        **Requirements:**
        1. Include appropriate badges (build, coverage, PyPI, Python versions, license)
        2. Write an engaging introduction that clearly explains what the package does
        3. Provide clear installation instructions (pip install)
        4. Include a quick start section with practical examples
        5. Document main features with code examples
        6. Add API reference or link to full documentation
        7. Include contributing guidelines
        8. Add license information
        9. Include links to issues, documentation, and repository
        10. Use proper Markdown formatting with headers, code blocks, and lists

        **Structure the README with these sections:**
        - Title and badges
        - Description and key features
        - Installation
        - Quick Start
        - Usage Examples
        - API Reference
        - Contributing
        - License
        - Changelog link



        Generate a professional, comprehensive README that would make users want to try the package."""