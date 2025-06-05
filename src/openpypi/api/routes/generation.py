"""
API routes for project generation.
"""

import asyncio  # Required for background tasks
import time  # Added import
import uuid  # Added import
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from openai import OpenAI

from openpypi.api.dependencies import get_api_key, get_config, get_openai_client
from openpypi.api.schemas import (
    APIResponse,
    ErrorResponse,
    GenerationResponse,
    ProjectGenerationResult,
    ProjectRequest,
    TaskStatus,
)
from openpypi.core.config import Config
from openpypi.core.generator import ProjectGenerator
from openpypi.core.openpypi import OpenPypi
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Temporary storage for task statuses. Replace with a persistent solution (e.g., Redis, DB) for production.
# Key: task_id, Value: TaskStatus object
task_status_db: Dict[str, TaskStatus] = {}


async def run_generation_task(
    task_id: str, idea_request: ProjectRequest, openpypi_instance: OpenPypi
):
    """Runs the project generation in the background and updates task status."""
    task_status_db[task_id] = TaskStatus(
        task_id=task_id,
        status="STARTED",
        progress=5,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    try:
        logger.info(
            f"Background task {task_id}: Starting project generation for idea: {idea_request.name[:50]}..."
        )

        # Determine output directory - this needs careful consideration in a real API
        # For now, using a temporary or pre-configured base directory
        # Ensure this path is secure and properly managed.
        base_output_dir = Path(
            openpypi_instance.config.get("project_generation_output_dir", "./generated_projects")
        )
        base_output_dir.mkdir(parents=True, exist_ok=True)

        project_output_dir = base_output_dir / (idea_request.name or f"proj_{task_id}")

        # Update task progress
        task_status_db[task_id].progress = 10
        task_status_db[task_id].updated_at = datetime.now(timezone.utc)

        result = await openpypi_instance.generate_complete_project(
            idea=idea_request.name,
            output_dir=project_output_dir,  # This should be a Path object
            package_name=idea_request.name,
            author=idea_request.author,
            email=idea_request.email,
            version=idea_request.version,
            description=idea_request.description,
            # Pass other relevant flags from ProjectRequest to generate_complete_project
            # Ensure generate_complete_project and its context handling are adapted for these
            use_fastapi=idea_request.use_fastapi,
            use_docker=idea_request.use_docker,
            use_openai=idea_request.use_openai,
            create_tests=idea_request.create_tests,
            initialize_git=idea_request.initialize_git,
        )

        task_status_db[task_id].progress = 90
        task_status_db[task_id].updated_at = datetime.now(timezone.utc)

        if result.get("success"):
            logger.info(f"Background task {task_id}: Project generation successful.")
            task_status_db[task_id].status = "SUCCESS"
            task_status_db[task_id].result = ProjectGenerationResult(
                package_name=result["package_name"],
                output_directory=str(result["output_directory"]),
                files_created=result["project_summary"].get(
                    "files_created", []
                ),  # Adjust based on actual result structure
                directories_created=result["project_summary"].get("directories_created", []),
                pipeline_summary=result["pipeline_results"],  # Or a more summarized version
            )
        else:
            logger.error(
                f"Background task {task_id}: Project generation failed. Error: {result.get('error')}"
            )
            task_status_db[task_id].status = "FAILURE"
            task_status_db[task_id].error_message = result.get("error", "Unknown generation error")

    except Exception as e:
        logger.error(
            f"Background task {task_id}: Exception during project generation: {e}", exc_info=True
        )
        task_status_db[task_id].status = "FAILURE"
        task_status_db[task_id].error_message = str(e)
    finally:
        task_status_db[task_id].progress = 100
        task_status_db[task_id].updated_at = datetime.now(timezone.utc)
        logger.info(
            f"Background task {task_id} finished with status: {task_status_db[task_id].status}"
        )


async def _generate_project_background(task_id: str, project_config: Config) -> None:
    """Background task to generate a project."""
    try:
        # Update task status
        if hasattr(generate_project_async, "tasks"):
            generate_project_async.tasks[task_id].update(
                {"status": "running", "updated_at": datetime.utcnow()}
            )

        # Generate the project
        generator = ProjectGenerator(project_config)
        result = generator.generate()

        # Update task status with success
        if hasattr(generate_project_async, "tasks"):
            generate_project_async.tasks[task_id].update(
                {
                    "status": "completed",
                    "updated_at": datetime.utcnow(),
                    "result": {
                        "project_name": project_config.project_name,
                        "package_name": project_config.package_name,
                        "files_created": result.get("files_created", []),
                        "directories_created": result.get("directories_created", []),
                        "warnings": result.get("warnings", []),
                    },
                }
            )

        logger.info(f"Background task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}")
        # Update task status with failure
        if hasattr(generate_project_async, "tasks"):
            generate_project_async.tasks[task_id].update(
                {"status": "failed", "updated_at": datetime.utcnow(), "error_message": str(e)}
            )


@router.post(
    "/async",
    response_model=APIResponse,  # Initially returns a TaskAccepted/TaskStatus response
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate New Python Project (Async)",
    description="Generates a complete Python project based on the provided parameters. This is an asynchronous operation.",
)
async def generate_project_async(
    project_request: ProjectRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    api_key: str = Depends(get_api_key),
    config: Config = Depends(get_config),
) -> APIResponse:
    """Endpoint to initiate asynchronous project generation."""
    import uuid

    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    try:
        # Store task in a simple in-memory store (in production, use Redis/DB)
        if not hasattr(generate_project_async, "tasks"):
            generate_project_async.tasks = {}

        generate_project_async.tasks[task_id] = {
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "project_name": project_request.name,
        }

        # Convert ProjectRequest to Config
        project_config = Config(
            project_name=project_request.name,
            package_name=project_request.name.lower().replace("-", "_").replace(" ", "_"),
            description=project_request.description,
            author=project_request.author,
            email=project_request.email,
            version=project_request.version or "0.1.0",
            use_fastapi=project_request.use_fastapi or True,
            use_docker=project_request.use_docker or True,
            use_openai=project_request.use_openai or True,
            create_tests=project_request.create_tests or True,
            test_framework=project_request.test_framework or "pytest",
            allow_overwrite=True,  # Allow overwriting for testing
        )

        # Override with options if provided
        if project_request.options:
            for key, value in project_request.options.items():
                if hasattr(project_config, key):
                    setattr(project_config, key, value)

        # Add background task
        background_tasks.add_task(_generate_project_background, task_id, project_config)

        logger.info(
            f"Async project generation started for {project_request.name}, task_id: {task_id}"
        )

        return APIResponse(
            success=True,
            message=f"Project generation started",
            data={"task_id": task_id, "status": "pending", "project_name": project_request.name},
        )
    except Exception as e:
        logger.error(f"Project generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project generation failed: {str(e)}",
        )


@router.get(
    "/status/{task_id}",
    response_model=APIResponse,
    summary="Get Task Status",
    description="Get the status of an asynchronous project generation task.",
)
async def get_generation_status(task_id: str) -> APIResponse:
    """Get the status of a background generation task."""
    if hasattr(generate_project_async, "tasks") and task_id in generate_project_async.tasks:
        task_info = generate_project_async.tasks[task_id]
        return APIResponse(success=True, message="Task status retrieved", data=task_info)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )


# Synchronous (direct call) endpoint for simpler testing or specific use cases if needed.
# This is generally NOT recommended for long-running tasks like project generation in a web API.
@router.post(
    "/sync",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate New Python Project (Sync)",
    description="Generates a complete Python project based on the provided parameters. This is a synchronous operation.",
)
async def generate_project_sync(
    project_request: ProjectRequest,
    request: Request,
    api_key: str = Depends(get_api_key),
    config: Config = Depends(get_config),
) -> APIResponse:
    """Endpoint to synchronously generate a new Python project."""
    try:
        # Convert ProjectRequest to Config
        project_config = Config(
            project_name=project_request.name,
            package_name=project_request.name.lower().replace("-", "_").replace(" ", "_"),
            description=project_request.description,
            author=project_request.author,
            email=project_request.email,
            version=project_request.version or "0.1.0",
            use_fastapi=project_request.use_fastapi or True,
            use_docker=project_request.use_docker or True,
            use_openai=project_request.use_openai or True,
            create_tests=project_request.create_tests or True,
            test_framework=project_request.test_framework or "pytest",
            allow_overwrite=True,  # Allow overwriting for testing
        )

        # Override with options if provided
        if project_request.options:
            for key, value in project_request.options.items():
                if hasattr(project_config, key):
                    setattr(project_config, key, value)

        # Generate the project
        generator = ProjectGenerator(project_config)
        result = generator.generate()

        logger.info(f"Project {project_request.name} generated successfully")

        return APIResponse(
            success=True,
            message=f"Project '{project_request.name}' generated successfully",
            data={
                "project_name": project_request.name,
                "package_name": project_config.package_name,
                "files_created": result.get("files_created", []),
                "directories_created": result.get("directories_created", []),
                "warnings": result.get("warnings", []),
            },
        )

    except Exception as e:
        logger.error(f"Project generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project generation failed: {str(e)}",
        )
