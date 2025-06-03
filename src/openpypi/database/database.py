"""
Database manager for OpenPypi with SQLAlchemy integration.
"""

import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from openpypi.utils.logger import get_logger

from .models import Base

logger = get_logger(__name__)


class DatabaseManager:
    """Comprehensive database manager with connection pooling and health monitoring."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager."""
        self.database_url = database_url or self._get_database_url()
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._health_check_interval = 30  # seconds
        self._last_health_check = 0
        self._is_healthy = False

    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        # Check for various database URL environment variables
        database_url = (
            os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URL") or os.getenv("DB_URL")
        )

        if not database_url:
            # Default to SQLite for development
            database_url = "sqlite:///./openpypi.db"
            logger.warning("No database URL found, using SQLite default: sqlite:///./openpypi.db")

        return database_url

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with optimized configuration."""
        parsed_url = urlparse(self.database_url)

        # Base engine configuration
        engine_config = {
            "echo": os.getenv("DB_ECHO", "false").lower() == "true",
            "future": True,  # Use SQLAlchemy 2.0 style
        }

        # Database-specific optimizations
        if parsed_url.scheme.startswith("postgresql"):
            engine_config.update(
                {
                    "poolclass": pool.QueuePool,
                    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                    "pool_pre_ping": True,
                    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
                    "connect_args": {
                        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
                        "application_name": "openpypi",
                    },
                }
            )
        elif parsed_url.scheme.startswith("mysql"):
            engine_config.update(
                {
                    "poolclass": pool.QueuePool,
                    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                    "pool_pre_ping": True,
                    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
                    "connect_args": {
                        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
                        "charset": "utf8mb4",
                    },
                }
            )
        elif parsed_url.scheme.startswith("sqlite"):
            engine_config.update(
                {
                    "poolclass": pool.StaticPool,
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
                    },
                }
            )

        engine = create_engine(self.database_url, **engine_config)

        # Add event listeners for connection management
        self._add_engine_events(engine)

        return engine

    def _add_engine_events(self, engine: Engine) -> None:
        """Add event listeners for database monitoring."""

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for performance and reliability."""
            if engine.dialect.name == "sqlite":
                cursor = dbapi_connection.cursor()
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                # Set journal mode to WAL for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                # Set synchronous mode for better performance
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Set temp store to memory
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()

        @event.listens_for(engine, "checkout")
        def checkout_listener(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkouts for monitoring."""
            logger.debug("Database connection checked out")

        @event.listens_for(engine, "checkin")
        def checkin_listener(dbapi_connection, connection_record):
            """Log connection checkins for monitoring."""
            logger.debug("Database connection checked in")

    def initialize(self) -> None:
        """Initialize database connection and create session factory."""
        try:
            logger.info(f"Initializing database connection to {self._mask_url(self.database_url)}")

            self.engine = self._create_engine()
            self.SessionLocal = sessionmaker(
                bind=self.engine, autocommit=False, autoflush=False, expire_on_commit=False
            )

            # Test connection
            self.health_check()

            logger.info("Database initialization completed successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            logger.info("Creating database tables")
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def drop_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        try:
            logger.warning("Dropping all database tables")
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        current_time = time.time()

        # Use cached result if within interval
        if (
            current_time - self._last_health_check
        ) < self._health_check_interval and self._is_healthy:
            return {"status": "healthy", "cached": True}

        try:
            start_time = time.time()

            with self.get_session() as session:
                # Simple query to test connection
                result = session.execute(text("SELECT 1")).scalar()

                if result != 1:
                    raise Exception("Health check query returned unexpected result")

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            self._is_healthy = True
            self._last_health_check = current_time

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "database_url": self._mask_url(self.database_url),
                "pool_size": self.engine.pool.size() if hasattr(self.engine.pool, "size") else None,
                "checked_out_connections": (
                    self.engine.pool.checkedout()
                    if hasattr(self.engine.pool, "checkedout")
                    else None
                ),
            }

        except (OperationalError, DisconnectionError) as e:
            self._is_healthy = False
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_url": self._mask_url(self.database_url),
            }
        except Exception as e:
            self._is_healthy = False
            logger.error(f"Database health check failed with unexpected error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_url": self._mask_url(self.database_url),
            }

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with proper cleanup."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_session_factory(self) -> sessionmaker:
        """Get session factory for dependency injection."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal

    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL."""
        try:
            parsed = urlparse(url)
            if parsed.password:
                masked_netloc = parsed.netloc.replace(parsed.password, "***")
                return parsed._replace(netloc=masked_netloc).geturl()
            return url
        except Exception:
            return "***masked***"

    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed connection information."""
        if not self.engine:
            return {"status": "not_initialized"}

        info = {
            "database_url": self._mask_url(self.database_url),
            "dialect": self.engine.dialect.name,
            "driver": self.engine.dialect.driver,
            "pool_class": self.engine.pool.__class__.__name__,
        }

        # Add pool-specific information
        if hasattr(self.engine.pool, "size"):
            info.update(
                {
                    "pool_size": self.engine.pool.size(),
                    "checked_out_connections": self.engine.pool.checkedout(),
                    "overflow_connections": self.engine.pool.overflow(),
                    "checked_in_connections": self.engine.pool.checkedin(),
                }
            )

        return info

    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            logger.info("Closing database connections")
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager


def get_db_session() -> Generator[Session, None, None]:
    """Dependency function for FastAPI to get database session."""
    db_manager = get_database_manager()
    with db_manager.get_session() as session:
        yield session


def init_database(
    database_url: Optional[str] = None, create_tables: bool = True
) -> DatabaseManager:
    """Initialize database with optional table creation."""
    global _db_manager

    _db_manager = DatabaseManager(database_url)
    _db_manager.initialize()

    if create_tables:
        _db_manager.create_tables()

    return _db_manager


def close_database() -> None:
    """Close database connections."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
