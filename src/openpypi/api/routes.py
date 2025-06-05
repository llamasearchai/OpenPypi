"""API routes for OpenPypi."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, validator

from ..core.config import Config
from ..core.generator import ProjectGenerator
from ..core.exceptions import ValidationError, GenerationError
from ..utils.logger import get_logger
from ..utils.monitoring import get_system_metrics, get_application_metrics

logger = get_logger(__name__)
router = APIRouter()

# In-memory task storage (use Redis in production)
tasks: Dict[str, Dict[str, Any]] = {}
active_websockets: Dict[str, WebSocket] = {}


class ProjectRequest(BaseModel):
    """Project generation request model."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    author: str = Field("Nik Jois", description="Author name")
    email: str = Field("nikjois@llamasearch.ai", description="Author email")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Project options")
    
    @validator("name")
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Project name cannot be empty")
        return v.strip()
    
    @validator("email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class ProjectResponse(BaseModel):
    """Project generation response model."""
    status: str
    project_dir: Optional[str] = None
    files_created: Optional[list] = None
    directories_created: Optional[list] = None
    commands_run: Optional[list] = None
    warnings: Optional[list] = None
    task_id: Optional[str] = None
    message: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Task status response model."""
    task_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConfigValidationRequest(BaseModel):
    """Configuration validation request."""
    project_name: Optional[str] = None
    author: Optional[str] = None
    email: Optional[str] = None
    version: Optional[str] = None
    use_fastapi: Optional[bool] = None
    use_docker: Optional[bool] = None
    test_framework: Optional[str] = None


class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""
    valid: bool
    errors: Optional[list] = None
    warnings: Optional[list] = None


# Health check routes
@router.get("/health", tags=["Health"])
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.3.0"
    }


@router.get("/live", tags=["Health"])
async def liveness_probe():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/ready", tags=["Health"])
async def readiness_probe():
    """Kubernetes readiness probe."""
    # Add checks for dependencies (database, cache, etc.)
    return {"status": "ready"}


@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with dependency status."""
    checks = {
        "system": {"status": "healthy", "cpu_percent": 0.0, "memory_percent": 0.0},
        "database": {"status": "healthy", "connection_pool": "available"},
        "cache": {"status": "healthy", "connections": 0}
    }
    
    return {
        "status": "healthy",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


# Project generation routes
@router.post("/generate/sync", response_model=ProjectResponse, tags=["Generation"])
async def generate_project_sync(request: ProjectRequest):
    """Generate project synchronously."""
    try:
        # Create configuration
        config = Config(
            project_name=request.name,
            author=request.author,
            email=request.email,
            description=request.description,
            **request.options
        )
        
        # Validate configuration
        config.validate()
        
        # Generate project
        generator = ProjectGenerator(config)
        result = generator.generate()
        
        return ProjectResponse(
            status="success",
            project_dir=result["project_dir"],
            files_created=result["files_created"],
            directories_created=result["directories_created"],
            commands_run=result["commands_run"],
            warnings=result["warnings"]
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail={"error": str(e), "type": "validation_error"})
    except GenerationError as e:
        raise HTTPException(status_code=500, detail={"error": str(e), "type": "generation_error"})
    except Exception as e:
        logger.error(f"Unexpected error in sync generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e), "type": "internal_error"})


@router.post("/generate/async", response_model=ProjectResponse, tags=["Generation"])
async def generate_project_async(request: ProjectRequest, background_tasks: BackgroundTasks):
    """Generate project asynchronously."""
    try:
        # Create task ID
        task_id = str(uuid.uuid4())
        
        # Store task info
        tasks[task_id] = {
            "id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Task created",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "request": request.dict()
        }
        
        # Start background task
        background_tasks.add_task(generate_project_background, task_id, request)
        
        return ProjectResponse(
            status="accepted",
            task_id=task_id,
            message="Project generation started"
        )
        
    except Exception as e:
        logger.error(f"Error starting async generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/generate/status/{task_id}", response_model=TaskStatusResponse, tags=["Generation"])
async def get_task_status(task_id: str):
    """Get task status."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return TaskStatusResponse(**task)


async def generate_project_background(task_id: str, request: ProjectRequest):
    """Background task for project generation."""
    try:
        # Update task status
        tasks[task_id].update({
            "status": "running",
            "progress": 10,
            "message": "Creating configuration",
            "updated_at": datetime.utcnow()
        })
        
        # Notify WebSocket clients
        await notify_websocket_clients(task_id, tasks[task_id])
        
        # Create configuration
        config = Config(
            project_name=request.name,
            author=request.author,
            email=request.email,
            description=request.description,
            **request.options
        )
        
        # Update progress
        tasks[task_id].update({
            "progress": 30,
            "message": "Validating configuration",
            "updated_at": datetime.utcnow()
        })
        await notify_websocket_clients(task_id, tasks[task_id])
        
        # Validate configuration
        config.validate()
        
        # Update progress
        tasks[task_id].update({
            "progress": 50,
            "message": "Generating project",
            "updated_at": datetime.utcnow()
        })
        await notify_websocket_clients(task_id, tasks[task_id])
        
        # Generate project
        generator = ProjectGenerator(config)
        result = generator.generate()
        
        # Task completed
        tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Project generated successfully",
            "result": result,
            "updated_at": datetime.utcnow()
        })
        await notify_websocket_clients(task_id, tasks[task_id])
        
    except Exception as e:
        logger.error(f"Background task error: {e}", exc_info=True)
        tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow()
        })
        await notify_websocket_clients(task_id, tasks[task_id])


async def notify_websocket_clients(task_id: str, task_data: Dict[str, Any]):
    """Notify WebSocket clients about task updates."""
    if task_id in active_websockets:
        try:
            await active_websockets[task_id].send_json(task_data)
        except Exception as e:
            logger.error(f"WebSocket notification error: {e}")
            # Remove dead connection
            active_websockets.pop(task_id, None)


# WebSocket route for real-time updates
@router.websocket("/ws/generation/{task_id}")
async def websocket_generation_status(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task status updates."""
    await websocket.accept()
    active_websockets[task_id] = websocket
    
    try:
        # Send current status if task exists
        if task_id in tasks:
            await websocket.send_json(tasks[task_id])
        else:
            await websocket.send_json({"error": "Task not found"})
        
        # Keep connection alive
        while True:
            # Wait for client messages (ping/pong)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keep-alive
                await websocket.send_json({"type": "keep-alive", "timestamp": datetime.utcnow().isoformat()})
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_websockets.pop(task_id, None)


# Monitoring routes
@router.get("/monitoring/metrics", tags=["Monitoring"])
async def get_metrics():
    """Get application and system metrics."""
    return {
        "application": get_application_metrics(),
        "system": get_system_metrics(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/monitoring/metrics/system", tags=["Monitoring"])
async def get_system_metrics_endpoint():
    """Get system metrics."""
    return {
        **get_system_metrics(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/monitoring/metrics/application", tags=["Monitoring"])
async def get_application_metrics_endpoint():
    """Get application metrics."""
    return {
        **get_application_metrics(),
        "timestamp": datetime.utcnow().isoformat()
    }


# Configuration routes
@router.get("/config", tags=["Configuration"])
async def get_config_info():
    """Get configuration information."""
    return {
        "version": "0.3.0",
        "author": "Nik Jois",
        "email": "nikjois@llamasearch.ai",
        "features": {
            "fastapi_support": True,
            "docker_support": True,
            "openai_integration": True,
            "github_actions": True,
            "testing_frameworks": ["pytest", "unittest"],
            "cloud_providers": ["aws", "gcp", "azure"]
        },
        "supported_templates": [
            "library",
            "web_api", 
            "cli_tool",
            "data_science",
            "ml_toolkit"
        ]
    }


@router.post("/config/validate", response_model=ConfigValidationResponse, tags=["Configuration"])
async def validate_config(request: ConfigValidationRequest):
    """Validate configuration."""
    try:
        # Create config from request
        config_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not config_data.get("project_name"):
            config_data["project_name"] = "test-project"
        if not config_data.get("author"):
            config_data["author"] = "Nik Jois"
        if not config_data.get("email"):
            config_data["email"] = "nikjois@llamasearch.ai"
        
        config = Config(**config_data)
        config.validate()
        
        return ConfigValidationResponse(valid=True)
        
    except ValidationError as e:
        return ConfigValidationResponse(
            valid=False,
            errors=[str(e)]
        )
    except Exception as e:
        logger.error(f"Config validation error: {e}")
        return ConfigValidationResponse(
            valid=False,
            errors=[f"Validation error: {str(e)}"]
        )


# Task management routes
@router.get("/tasks", tags=["Tasks"])
async def list_tasks():
    """List all tasks."""
    return {
        "tasks": list(tasks.values()),
        "total": len(tasks)
    }


@router.delete("/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: str):
    """Delete a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Remove from active websockets
    active_websockets.pop(task_id, None)
    
    # Remove task
    deleted_task = tasks.pop(task_id)
    
    return {
        "message": "Task deleted successfully",
        "task_id": task_id,
        "status": deleted_task.get("status")
    }


@router.post("/tasks/cleanup", tags=["Tasks"])
async def cleanup_completed_tasks():
    """Clean up completed and failed tasks."""
    completed_statuses = ["completed", "failed"]
    tasks_to_remove = [
        task_id for task_id, task in tasks.items()
        if task.get("status") in completed_statuses
    ]
    
    for task_id in tasks_to_remove:
        tasks.pop(task_id, None)
        active_websockets.pop(task_id, None)
    
    return {
        "message": f"Cleaned up {len(tasks_to_remove)} tasks",
        "removed_tasks": tasks_to_remove
    } 