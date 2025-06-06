"""
Admin API endpoints for OpenPypi.
Provides administrative functions for system management, user administration, and monitoring.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from openpypi.api.dependencies import get_current_admin_user, get_db
from openpypi.database.models import ApiKey, AuditLog, Package, Project, User, UserRole, UserStatus
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
    responses={403: {"description": "Admin access required"}},
)


# Response Models
class SystemStatsResponse(BaseModel):
    """System statistics response."""

    total_users: int
    active_users: int
    total_projects: int
    total_packages: int
    successful_builds: int
    failed_builds: int
    total_downloads: int


class UserAdminResponse(BaseModel):
    """Admin user response with sensitive information."""

    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    status: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    project_count: int
    package_count: int


class UserListResponse(BaseModel):
    """User list response for admin."""

    users: List[UserAdminResponse]
    total: int
    page: int
    per_page: int


class ProjectAdminResponse(BaseModel):
    """Admin project response."""

    id: str
    name: str
    description: Optional[str]
    version: str
    status: str
    owner_username: str
    owner_email: str
    created_at: datetime
    package_count: int
    download_count: int


class AuditLogResponse(BaseModel):
    """Audit log response."""

    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    user_id: Optional[str]
    username: Optional[str]
    ip_address: Optional[str]
    success: bool
    created_at: datetime
    extra_data: Dict[str, Any]


# System Statistics
@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(db: Session = Depends(get_db)):
    """Get comprehensive system statistics."""

    # User statistics
    total_users = db.query(User).count()
    active_users = (
        db.query(User)
        .filter(and_(User.is_active == True, User.status == UserStatus.ACTIVE))
        .count()
    )

    # Project statistics
    total_projects = db.query(Project).count()

    # Package statistics
    total_packages = db.query(Package).count()
    successful_builds = db.query(Package).filter(Package.status == "success").count()
    failed_builds = db.query(Package).filter(Package.status == "failed").count()

    # Download statistics
    total_downloads = db.query(func.sum(Package.downloads)).scalar() or 0

    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_projects=total_projects,
        total_packages=total_packages,
        successful_builds=successful_builds,
        failed_builds=failed_builds,
        total_downloads=total_downloads,
    )


# User Management
@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all users with admin details."""

    query = db.query(User)

    # Apply filters
    if status_filter:
        query = query.filter(User.status == status_filter)

    if role_filter:
        query = query.filter(User.role == role_filter)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            User.username.ilike(search_term)
            | User.email.ilike(search_term)
            | User.full_name.ilike(search_term)
        )

    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()

    # Get additional stats for each user
    user_responses = []
    for user in users:
        project_count = db.query(Project).filter(Project.owner_id == user.id).count()
        package_count = db.query(Package).join(Project).filter(Project.owner_id == user.id).count()

        user_responses.append(
            UserAdminResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                status=user.status.value,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                last_login=user.last_login,
                project_count=project_count,
                package_count=package_count,
            )
        )

    return UserListResponse(users=user_responses, total=total, page=page, per_page=per_page)


@router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, status: UserStatus, db: Session = Depends(get_db)):
    """Update user status (activate, suspend, etc.)."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.status = status
    user.is_active = status == UserStatus.ACTIVE
    db.commit()

    logger.info(f"Admin updated user {user.username} status to {status.value}")

    return {"message": f"User status updated to {status.value}"}


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: UserRole, db: Session = Depends(get_db)):
    """Update user role."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = role
    db.commit()

    logger.info(f"Admin updated user {user.username} role to {role.value}")

    return {"message": f"User role updated to {role.value}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Delete a user account (admin only)."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent deletion of super admin
    if user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete super admin user"
        )

    username = user.username
    db.delete(user)
    db.commit()

    logger.warning(f"Admin deleted user account: {username}")

    return {"message": f"User {username} deleted successfully"}


# Project Management
@router.get("/projects")
async def list_all_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all projects across all users."""

    query = db.query(Project).join(User)

    if status_filter:
        query = query.filter(Project.status == status_filter)

    total = query.count()
    projects = query.offset((page - 1) * per_page).limit(per_page).all()

    project_responses = []
    for project in projects:
        package_count = db.query(Package).filter(Package.project_id == project.id).count()

        project_responses.append(
            ProjectAdminResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                version=project.version,
                status=project.status.value,
                owner_username=project.owner.username,
                owner_email=project.owner.email,
                created_at=project.created_at,
                package_count=package_count,
                download_count=project.download_count,
            )
        )

    return {"projects": project_responses, "total": total, "page": page, "per_page": per_page}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project (admin only)."""

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project_name = project.name
    owner_username = project.owner.username

    db.delete(project)
    db.commit()

    logger.warning(f"Admin deleted project: {project_name} (owner: {owner_username})")

    return {"message": f"Project {project_name} deleted successfully"}


# Audit Logs
@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action_filter: Optional[str] = None,
    user_id_filter: Optional[str] = None,
    days_back: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get audit logs for security and compliance monitoring."""

    # Filter by date range
    since_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    query = db.query(AuditLog).filter(AuditLog.created_at >= since_date)

    # Apply filters
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    if user_id_filter:
        query = query.filter(AuditLog.user_id == user_id_filter)

    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())

    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    log_responses = []
    for log in logs:
        log_responses.append(
            AuditLogResponse(
                id=log.id,
                action=log.action.value,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                user_id=log.user_id,
                username=log.user.username if log.user else None,
                ip_address=log.ip_address,
                success=log.success,
                created_at=log.created_at,
                extra_data=log.extra_data,
            )
        )

    return {
        "logs": log_responses,
        "total": total,
        "page": page,
        "per_page": per_page,
        "days_back": days_back,
    }


# System Maintenance
@router.post("/maintenance/cleanup")
async def cleanup_system(
    cleanup_failed_builds: bool = True,
    cleanup_old_logs: bool = True,
    days_to_keep: int = 30,
    db: Session = Depends(get_db),
):
    """Perform system cleanup operations."""

    cleanup_results = {}

    if cleanup_failed_builds:
        # Delete failed packages older than specified days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        failed_packages = db.query(Package).filter(
            and_(Package.status == "failed", Package.created_at < cutoff_date)
        )
        count = failed_packages.count()
        failed_packages.delete()
        cleanup_results["failed_packages_removed"] = count

    if cleanup_old_logs:
        # Clean up old audit logs
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        old_logs = db.query(AuditLog).filter(AuditLog.created_at < cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        cleanup_results["old_logs_removed"] = count

    db.commit()

    logger.info(f"Admin performed system cleanup: {cleanup_results}")

    return {"message": "System cleanup completed", "results": cleanup_results}


@router.get("/health/detailed")
async def get_detailed_health(db: Session = Depends(get_db)):
    """Get detailed system health information."""

    # Database connectivity
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Recent error rate
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_errors = (
        db.query(AuditLog)
        .filter(and_(AuditLog.created_at >= recent_time, AuditLog.success == False))
        .count()
    )

    recent_total = db.query(AuditLog).filter(AuditLog.created_at >= recent_time).count()
    error_rate = (recent_errors / recent_total * 100) if recent_total > 0 else 0

    # Build success rate
    recent_builds = db.query(Package).filter(Package.created_at >= recent_time).count()
    recent_failed_builds = (
        db.query(Package)
        .filter(and_(Package.created_at >= recent_time, Package.status == "failed"))
        .count()
    )

    build_success_rate = (
        ((recent_builds - recent_failed_builds) / recent_builds * 100) if recent_builds > 0 else 100
    )

    return {
        "database": db_status,
        "error_rate_1h": f"{error_rate:.2f}%",
        "build_success_rate_1h": f"{build_success_rate:.2f}%",
        "recent_errors": recent_errors,
        "recent_builds": recent_builds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
