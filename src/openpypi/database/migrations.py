"""
Database migration manager for OpenPypi using Alembic.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from openpypi.utils.logger import get_logger

logger = get_logger(__name__)


class MigrationManager:
    """Database migration manager using Alembic."""

    def __init__(self, database_url: str, migrations_dir: Optional[Path] = None):
        """Initialize migration manager."""
        self.database_url = database_url
        self.migrations_dir = migrations_dir or (Path(__file__).parent / "migrations")
        self.alembic_cfg = self._create_alembic_config()

    def _create_alembic_config(self) -> AlembicConfig:
        """Create Alembic configuration."""
        # Create migrations directory if it doesn't exist
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Create alembic.ini configuration
        alembic_ini_path = self.migrations_dir / "alembic.ini"
        if not alembic_ini_path.exists():
            self._create_alembic_ini(alembic_ini_path)

        # Create Alembic config
        alembic_cfg = AlembicConfig(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(self.migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)

        return alembic_cfg

    def _create_alembic_ini(self, ini_path: Path) -> None:
        """Create alembic.ini configuration file."""
        ini_content = f"""# OpenPypi Alembic Configuration

[alembic]
# path to migration scripts
script_location = {self.migrations_dir}

# template used to generate migration file names
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
timezone = UTC

# max length of characters to apply to the "slug" field
truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
sourceless = false

# version location specification
version_locations = %(here)s/versions

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
output_encoding = utf-8

sqlalchemy.url = {self.database_url}

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.

# format using "black" - use the console_scripts runner, against the "black" entrypoint
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
        ini_path.write_text(ini_content)
        logger.info(f"Created Alembic configuration at {ini_path}")

    def init_migrations(self) -> None:
        """Initialize Alembic migrations directory."""
        try:
            # Create the migrations directory structure
            versions_dir = self.migrations_dir / "versions"
            versions_dir.mkdir(parents=True, exist_ok=True)

            # Create env.py
            env_py_path = self.migrations_dir / "env.py"
            if not env_py_path.exists():
                self._create_env_py(env_py_path)

            # Create script.py.mako
            script_mako_path = self.migrations_dir / "script.py.mako"
            if not script_mako_path.exists():
                self._create_script_mako(script_mako_path)

            logger.info("Alembic migrations initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize migrations: {e}")
            raise

    def _create_env_py(self, env_path: Path) -> None:
        """Create env.py file for Alembic."""
        env_content = '''"""
Alembic environment configuration for OpenPypi.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from openpypi.database.models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_url():
    """Get database URL from environment or config."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        env_path.write_text(env_content)

    def _create_script_mako(self, script_path: Path) -> None:
        """Create script.py.mako template."""
        script_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade database schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database schema."""
    ${downgrades if downgrades else "pass"}
'''
        script_path.write_text(script_content)

    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """Create a new migration."""
        try:
            logger.info(f"Creating migration: {message}")

            if autogenerate:
                command.revision(self.alembic_cfg, message=message, autogenerate=True)
            else:
                command.revision(self.alembic_cfg, message=message)

            logger.info("Migration created successfully")
            return "success"

        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise

    def upgrade(self, revision: str = "head") -> None:
        """Upgrade database to specified revision."""
        try:
            logger.info(f"Upgrading database to revision: {revision}")
            command.upgrade(self.alembic_cfg, revision)
            logger.info("Database upgrade completed successfully")

        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            raise

    def downgrade(self, revision: str) -> None:
        """Downgrade database to specified revision."""
        try:
            logger.info(f"Downgrading database to revision: {revision}")
            command.downgrade(self.alembic_cfg, revision)
            logger.info("Database downgrade completed successfully")

        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            raise

    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()

        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            history = []

            for revision in script_dir.walk_revisions():
                history.append(
                    {
                        "revision": revision.revision,
                        "down_revision": revision.down_revision,
                        "branch_labels": revision.branch_labels,
                        "depends_on": revision.depends_on,
                        "doc": revision.doc,
                        "create_date": getattr(revision, "create_date", None),
                    }
                )

            return history

        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []

    def check_pending_migrations(self) -> bool:
        """Check if there are pending migrations."""
        try:
            engine = create_engine(self.database_url)
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)

            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                head_rev = script_dir.get_current_head()

                return current_rev != head_rev

        except Exception as e:
            logger.error(f"Failed to check pending migrations: {e}")
            return True  # Assume pending if we can't check

    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status."""
        try:
            current_revision = self.get_current_revision()
            history = self.get_migration_history()
            pending = self.check_pending_migrations()

            # Get head revision
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            head_revision = script_dir.get_current_head()

            return {
                "current_revision": current_revision,
                "head_revision": head_revision,
                "pending_migrations": pending,
                "total_migrations": len(history),
                "migration_history": history[:5],  # Last 5 migrations
                "database_url_masked": self._mask_url(self.database_url),
                "migrations_directory": str(self.migrations_dir),
            }

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e), "database_url_masked": self._mask_url(self.database_url)}

    def stamp_database(self, revision: str = "head") -> None:
        """Stamp database with specified revision without running migrations."""
        try:
            logger.info(f"Stamping database with revision: {revision}")
            command.stamp(self.alembic_cfg, revision)
            logger.info("Database stamped successfully")

        except Exception as e:
            logger.error(f"Failed to stamp database: {e}")
            raise

    def show_migration(self, revision: str) -> Dict[str, Any]:
        """Show details of a specific migration."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            script = script_dir.get_revision(revision)

            if not script:
                return {"error": f"Migration {revision} not found"}

            return {
                "revision": script.revision,
                "down_revision": script.down_revision,
                "branch_labels": script.branch_labels,
                "depends_on": script.depends_on,
                "doc": script.doc,
                "path": script.path,
                "create_date": getattr(script, "create_date", None),
            }

        except Exception as e:
            logger.error(f"Failed to show migration {revision}: {e}")
            return {"error": str(e)}

    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            if parsed.password:
                masked_netloc = parsed.netloc.replace(parsed.password, "***")
                return parsed._replace(netloc=masked_netloc).geturl()
            return url
        except Exception:
            return "***masked***"


def create_migration_manager(database_url: str) -> MigrationManager:
    """Create and initialize migration manager."""
    manager = MigrationManager(database_url)

    # Initialize migrations if not already done
    if not (manager.migrations_dir / "env.py").exists():
        manager.init_migrations()

    return manager
