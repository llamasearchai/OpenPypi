"""
Database session management for OpenPypi
Provides async SQLAlchemy session handling with proper connection pooling and error handling
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from openpypi.core.config import get_settings

logger = structlog.get_logger(__name__)

# Global variables for engine and session makers
engine: Optional[AsyncEngine] = None
async_session: Optional[async_sessionmaker[AsyncSession]] = None
sync_engine = None
sync_session: Optional[sessionmaker[Session]] = None


def get_database_url(async_driver: bool = True) -> str:
    """Get the database URL with appropriate driver for async or sync."""
    settings = get_settings()
    url = settings.database_url

    if async_driver and url.startswith("postgresql://"):
        # Use asyncpg for async PostgreSQL connections
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not async_driver and url.startswith("postgresql+asyncpg://"):
        # Use psycopg2 for sync PostgreSQL connections
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif url.startswith("sqlite://"):
        if async_driver:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    return url


def create_database_engine(async_engine: bool = True) -> AsyncEngine:
    """Create and configure database engine with proper settings."""
    settings = get_settings()
    database_url = get_database_url(async_driver=async_engine)

    # Engine configuration based on environment and database type
    engine_kwargs = {
        "echo": settings.app_env == "development",
        "future": True,
    }

    # Configure connection pooling
    if "postgresql" in database_url:
        engine_kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600,  # 1 hour
            }
        )
    elif "sqlite" in database_url:
        # SQLite specific configuration
        engine_kwargs.update(
            {
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 20,
                },
            }
        )

    if async_engine:
        return create_async_engine(database_url, **engine_kwargs)
    else:
        return create_engine(database_url, **engine_kwargs)


def setup_engine_events(engine_instance):
    """Set up database engine events for monitoring and logging."""

    @event.listens_for(engine_instance, "connect")
    def receive_connect(dbapi_connection, connection_record):
        logger.debug("Database connection established")

        # Enable foreign keys for SQLite
        if "sqlite" in str(engine_instance.url):
            with dbapi_connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine_instance, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        logger.debug("Database connection checked out from pool")

    @event.listens_for(engine_instance, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        logger.debug("Database connection returned to pool")


async def init_database():
    """Initialize database connections and session makers."""
    global engine, async_session, sync_engine, sync_session

    try:
        # Create async engine
        engine = create_database_engine(async_engine=True)
        setup_engine_events(engine)

        # Create async session maker
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

        # Create sync engine for migrations and other sync operations
        sync_engine = create_database_engine(async_engine=False)
        sync_session = sessionmaker(
            sync_engine,
            autoflush=True,
            autocommit=False,
        )

        # Test connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


async def close_database():
    """Close database connections and clean up resources."""
    global engine, sync_engine

    try:
        if engine:
            await engine.dispose()
            logger.info("Async database engine disposed")

        if sync_engine:
            sync_engine.dispose()
            logger.info("Sync database engine disposed")

    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    Used with FastAPI dependency injection.
    """
    if not async_session:
        await init_database()

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager to get database session.
    Use this for manual session management outside of FastAPI.
    """
    if not async_session:
        await init_database()

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """
    Get synchronous database session.
    Use this for migrations and other sync operations.
    """
    if not sync_session:
        # Initialize sync components if not already done
        global sync_engine
        sync_engine = create_database_engine(async_engine=False)
        setup_engine_events(sync_engine)
        sync_session = sessionmaker(sync_engine, autoflush=True, autocommit=False)

    return sync_session()


class DatabaseHealthCheck:
    """Database health check utility."""

    @staticmethod
    async def check_async_connection() -> bool:
        """Check if async database connection is healthy."""
        try:
            if not engine:
                return False

            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("Async database health check failed", error=str(e))
            return False

    @staticmethod
    def check_sync_connection() -> bool:
        """Check if sync database connection is healthy."""
        try:
            if not sync_engine:
                return False

            with sync_engine.begin() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("Sync database health check failed", error=str(e))
            return False

    @staticmethod
    async def get_connection_info() -> dict:
        """Get database connection information."""
        try:
            info = {
                "async_engine_initialized": engine is not None,
                "sync_engine_initialized": sync_engine is not None,
                "database_url": get_database_url(async_driver=True),
            }

            if engine:
                info.update(
                    {
                        "async_pool_size": engine.pool.size(),
                        "async_checked_out": engine.pool.checkedout(),
                        "async_overflow": engine.pool.overflow(),
                        "async_checked_in": engine.pool.checkedin(),
                    }
                )

            return info
        except Exception as e:
            logger.error("Error getting connection info", error=str(e))
            return {"error": str(e)}


# Initialize database on import in production
if os.getenv("APP_ENV") == "production":
    asyncio.create_task(init_database())
