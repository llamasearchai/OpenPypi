"""
Stage 1: Conceptualization - Refine and expand the package concept.
"""

import json
from typing import Any, Dict

from openpypi.core.context import PackageContext
from openpypi.stages.base import BaseStage
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class ConceptualizerStage(BaseStage):
    """
    Stage 1: Conceptualization

    This stage takes the initial package idea and refines it into a
    comprehensive concept with clear objectives, features, and scope.
    """

    async def execute(self, context: PackageContext) -> None:
        """Execute the conceptualization stage."""
        self.log_stage_start()

        try:
            # Generate refined concept
            system_prompt = self.get_system_prompt()
            user_prompt = self.get_user_prompt(context)

            response = await self.provider.generate_response(
                prompt=user_prompt, system_prompt=system_prompt, temperature=0.7
            )

            # Parse and validate response
            concept_data = await self._parse_concept_response(response["content"])

            if await self.validate_output(concept_data):
                # Update context with refined concept
                context.description = concept_data.get("description", "")
                context.keywords = concept_data.get("keywords", [])
                context.features.extend(concept_data.get("features", []))

                # Store stage output
                context.set_stage_output("p1_concept", concept_data)

                self.log_stage_end()
            else:
                raise ValueError("Invalid concept output generated")

        except Exception as e:
            self.log_stage_error(e)
            raise

    def get_system_prompt(self) -> str:
        """Get the system prompt for conceptualization."""
        return """You are an expert Python package architect and product manager. Your role is to take initial package ideas and refine them into comprehensive, well-defined concepts that can be implemented as production-ready Python packages.

        You excel at:
        - Understanding user needs and translating them into technical requirements
        - Identifying the core value proposition of a package
        - Defining clear scope and boundaries
        - Suggesting appropriate features and functionality
        - Considering the Python ecosystem and existing solutions
        - Ensuring the concept is feasible and valuable

        Always respond with structured JSON output that includes:
        - Refined description
        - Core objectives
        - Key features
        - Target audience
        - Use cases
        - Success criteria
        - Keywords for discoverability
        """

    def get_user_prompt(self, context: PackageContext) -> str:
        """Get the user prompt for conceptualization."""
        return f"""Please refine and expand the following package concept:

        **Original Idea:** {context.idea}

        **Package Type:** {context.package_type}
        **Target Python Version:** {context.python_version}
        **Requested Features:** {', '.join(context.features) if context.features else 'None specified'}
        **Constraints:** {', '.join(context.constraints) if context.constraints else 'None specified'}

        Please provide a comprehensive concept refinement in the following JSON format:

        {{
            "refined_description": "Clear, concise description of what the package does",
            "core_objectives": ["Primary goal 1", "Primary goal 2", "..."],
            "key_features": ["Feature 1", "Feature 2", "..."],
            "target_audience": ["Developer type 1", "Use case 1", "..."],
            "use_cases": [
                {{
                    "title": "Use case title",
                    "description": "Detailed description",
                    "example": "Code example or scenario"
                }}
            ],
            "success_criteria": ["Measurable success criterion 1", "..."],
            "keywords": ["keyword1", "keyword2", "..."],
            "scope": {{
                "included": ["What will be included"],
                "excluded": ["What will be explicitly excluded"],
                "future_considerations": ["Potential future features"]
            }},
            "ecosystem_analysis": {{
                "existing_solutions": ["Similar package 1", "Similar package 2"],
                "differentiation": "How this package will be different/better",
                "dependencies": ["Suggested core dependencies"]
            }},
            "technical_considerations": {{
                "complexity_level": "low|medium|high",
                "estimated_modules": 3-10,
                "architecture_style": "monolithic|modular|plugin-based",
                "async_support": true/false
            }}
        }}

        Ensure the concept is:
        1. Technically feasible with Python
        2. Valuable to the target audience
        3. Appropriately scoped (not too broad or narrow)
        4. Differentiated from existing solutions
        5. Aligned with Python ecosystem best practices
        """

    async def _parse_concept_response(self, response_content: str) -> Dict[str, Any]:
        """Parse the concept response from the AI."""
        try:
            # Try to parse as JSON
            concept_data = json.loads(response_content)
            return concept_data
        except json.JSONDecodeError:
            # Fallback: extract key information from text
            logger.warning("Failed to parse JSON response, using fallback extraction")

            # Basic fallback extraction
            lines = response_content.split("\n")
            concept_data = {
                "refined_description": "AI-generated package concept",
                "core_objectives": ["Provide useful functionality"],
                "key_features": ["Core functionality"],
                "target_audience": ["Python developers"],
                "use_cases": [
                    {
                        "title": "General use",
                        "description": "General purpose usage",
                        "example": "# Example usage",
                    }
                ],
                "success_criteria": ["Package works as expected"],
                "keywords": ["python", "utility"],
                "scope": {
                    "included": ["Core functionality"],
                    "excluded": ["Advanced features"],
                    "future_considerations": ["Enhancements"],
                },
                "ecosystem_analysis": {
                    "existing_solutions": [],
                    "differentiation": "Unique approach",
                    "dependencies": [],
                },
                "technical_considerations": {
                    "complexity_level": "medium",
                    "estimated_modules": 5,
                    "architecture_style": "modular",
                    "async_support": False,
                },
            }

            return concept_data

    async def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate the conceptualization output."""
        required_fields = [
            "refined_description",
            "core_objectives",
            "key_features",
            "target_audience",
        ]

        for field in required_fields:
            if field not in output:
                logger.error(f"Missing required field in concept output: {field}")
                return False

        # Validate that lists are not empty
        list_fields = ["core_objectives", "key_features", "target_audience"]
        for field in list_fields:
            if not output.get(field) or len(output[field]) == 0:
                logger.error(f"Field {field} cannot be empty")
                return False

        return True
