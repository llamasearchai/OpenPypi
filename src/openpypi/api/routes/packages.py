"""
Package management API endpoints for OpenPypi.
Handles package creation, deployment, version management, and publishing.
"""

import asyncio
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from openpypi.api.dependencies import get_current_user, get_db
from openpypi.core import Config, ProjectGenerator
from openpypi.core.context import PackageContext
from openpypi.core.orchestrator import PipelineOrchestrator
from openpypi.database.models import Package, Project, User
from openpypi.providers import get_provider_registry
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/packages",
    tags=["packages"],
    dependencies=[],
    responses={404: {"description": "Package not found"}},
)


# Request/Response Models
class PackageCreateRequest(BaseModel):
    """Request model for creating a new package."""
    project_id: str
    version: Optional[str] = "0.1.0"
    build_options: Dict[str, Any] = {}
    deployment_options: Dict[str, Any] = {}
    
    @validator('version')
    def validate_version(cls, v):
        """Validate semantic version format."""
        import re
        if not re.match(r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9-]+)?$', v):
            raise ValueError('Version must follow semantic versioning (e.g., 1.0.0)')
        return v


class PackageResponse(BaseModel):
    """Response model for package information."""
    id: str
    name: str
    version: str
    status: str
    project_id: str
    created_at: datetime
    build_duration: Optional[float]
    file_size: Optional[int]
    downloads: int


class PackageListResponse(BaseModel):
    """Response model for package list."""
    packages: List[PackageResponse]
    total: int
    page: int
    per_page: int


class BuildLogResponse(BaseModel):
    """Response model for build logs."""
    package_id: str
    logs: str
    status: str
    created_at: datetime


# Package Management Endpoints
@router.post("/", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    request: PackageCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create and build a new package from a project.
    
    This endpoint initiates the package building process, including:
    - Code generation and packaging
    - Dependency resolution
    - Testing and validation
    - Documentation generation
    """
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    # Create package record
    package = Package(
        name=project.name,
        version=request.version,
        project_id=project.id,
        status="pending"
    )
    
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Start build process in background
    background_tasks.add_task(
        build_package_async,
        package.id,
        project,
        request.build_options
    )
    
    logger.info(f"Started package build: {package.id} for project {project.name}")
    
    return PackageResponse(
        id=package.id,
        name=package.name,
        version=package.version,
        status=package.status,
        project_id=package.project_id,
        created_at=package.created_at,
        build_duration=package.build_duration,
        file_size=package.file_size,
        downloads=package.downloads
    )


@router.get("/", response_model=PackageListResponse)
async def list_packages(
    project_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List packages with optional filtering."""
    query = db.query(Package).join(Project).filter(Project.owner_id == current_user.id)
    
    if project_id:
        query = query.filter(Package.project_id == project_id)
    
    if status_filter:
        query = query.filter(Package.status == status_filter)
    
    total = query.count()
    
    packages = query.offset((page - 1) * per_page).limit(per_page).all()
    
    package_responses = [
        PackageResponse(
            id=pkg.id,
            name=pkg.name,
            version=pkg.version,
            status=pkg.status,
            project_id=pkg.project_id,
            created_at=pkg.created_at,
            build_duration=pkg.build_duration,
            file_size=pkg.file_size,
            downloads=pkg.downloads
        )
        for pkg in packages
    ]
    
    return PackageListResponse(
        packages=package_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific package."""
    package = db.query(Package).join(Project).filter(
        Package.id == package_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    return PackageResponse(
        id=package.id,
        name=package.name,
        version=package.version,
        status=package.status,
        project_id=package.project_id,
        created_at=package.created_at,
        build_duration=package.build_duration,
        file_size=package.file_size,
        downloads=package.downloads
    )


@router.get("/{package_id}/logs", response_model=BuildLogResponse)
async def get_build_logs(
    package_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get build logs for a package."""
    package = db.query(Package).join(Project).filter(
        Package.id == package_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    return BuildLogResponse(
        package_id=package.id,
        logs=package.build_log or "No logs available",
        status=package.status,
        created_at=package.created_at
    )


@router.post("/{package_id}/rebuild")
async def rebuild_package(
    package_id: str,
    background_tasks: BackgroundTasks,
    build_options: Dict[str, Any] = {},
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rebuild an existing package."""
    package = db.query(Package).join(Project).filter(
        Package.id == package_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    # Reset package status
    package.status = "pending"
    package.build_log = None
    package.error_message = None
    db.commit()
    
    # Start rebuild process
    background_tasks.add_task(
        build_package_async,
        package.id,
        package.project,
        build_options
    )
    
    return {"message": "Package rebuild started", "package_id": package.id}


@router.delete("/{package_id}")
async def delete_package(
    package_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a package."""
    package = db.query(Package).join(Project).filter(
        Package.id == package_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    db.delete(package)
    db.commit()
    
    return {"message": "Package deleted successfully"}


@router.get("/{package_id}/download")
async def download_package(
    package_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a built package."""
    package = db.query(Package).join(Project).filter(
        Package.id == package_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    if package.status != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Package is not ready for download"
        )
    
    # For demo purposes - in production, serve from proper storage
    return {"message": "Package download would be available here", "package_id": package.id}


# Background Tasks
async def build_package_async(package_id: str, project: Project, build_options: Dict[str, Any]):
    """Build a package asynchronously."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create new DB session for background task
    engine = create_engine("sqlite:///./openpypi.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        package = db.query(Package).filter(Package.id == package_id).first()
        if not package:
            return
        
        package.status = "building"
        db.commit()
        
        logger.info(f"Building package {package.name} v{package.version}")
        
        # Simulate build process
        await asyncio.sleep(2)  # Simulate build time
        
        # In a real implementation, this would:
        # 1. Generate code using the project configuration
        # 2. Run tests
        # 3. Build the package
        # 4. Generate documentation
        # 5. Validate the build
        
        # Update package status
        package.status = "success"
        package.build_duration = 2.0
        package.file_size = 1024 * 50  # 50KB
        package.build_log = "Package built successfully"
        
        db.commit()
        logger.info(f"Package {package.name} built successfully")
        
    except Exception as e:
        logger.error(f"Package build failed: {e}")
        if package:
            package.status = "failed"
            package.error_message = str(e)
            package.build_log = f"Build failed: {e}"
            db.commit()
    finally:
        db.close() 