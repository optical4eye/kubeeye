#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye initialization script
For initialization work when starting the Docker container
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Performance optimization: use uvloop for better asyncio performance
try:
    import uvloop
except ImportError:
    uvloop = None  # uvloop not available, use default asyncio

# Setup logger
from core.logging import get_logger
from core.config.settings import settings

logger = get_logger(__name__)


def ensure_data_directories():
    """Ensure data directories exist"""
    data_dir = Path(settings.kubeeye_data_dir)

    # Create only necessary directories for PostgreSQL + GitOps setup
    # clusters, results, schedules are now stored in PostgreSQL
    # Only git_rules remain in filesystem
    directories = [
        data_dir / "git_rules",  # GitOps rules from repositories
    ]

    for directory in directories:
        os.makedirs(str(directory), exist_ok=True)
        logger.info(f"Ensure directory exists: {directory}")


async def ensure_database():
    """Ensure database tables exist with retry mechanism"""
    try:
        from db.database import init_database, health_check

        logger.info("Initializing database with retry mechanism...")

        # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ Р±Р°Р·С‹ РґР°РЅРЅС‹С…
        await init_database()

        # РџСЂРѕРІРµСЂРєР° СЃРѕСЃС‚РѕСЏРЅРёСЏ
        health = await health_check()
        if health.get("status") == "healthy":
            logger.info("Database initialization completed successfully")
        else:
            logger.warning(f"Database initialization completed with warnings: {health.get('message')}")

    except Exception as e:
        logger.warning(f"Database initialization failed (this is normal during Docker build): {e}")
        logger.warning("Database will be initialized when the application starts with retry mechanism")
        # Don't raise exception during Docker build


def ensure_opa_binary():
    """Ensure OPA binary is working"""
    import subprocess

    opa_path = Path("/usr/local/bin/opa")

    logger.info(f"Checking OPA binary at {opa_path}")

    # Check if OPA exists
    if not opa_path.exists():
        logger.error(f"OPA binary does not exist at {opa_path}")
        raise RuntimeError(f"OPA binary not found at {opa_path}")

    # Check permissions
    stat_info = opa_path.stat()
    permissions = stat_info.st_mode & 0o777
    logger.info(f"OPA binary permissions: {oct(permissions)}")

    if not (stat_info.st_mode & 0o111):
        logger.error(f"OPA binary is not executable. Permissions: {oct(permissions)}")
        raise RuntimeError("OPA binary is not executable")

    # Test if OPA can be executed
    try:
        logger.info("Testing OPA execution...")
        result = subprocess.run([str(opa_path), "version"], capture_output=True, text=True, timeout=10)
        logger.info(f"OPA test result: returncode={result.returncode}")
        if result.stdout:
            logger.info(f"OPA stdout: {result.stdout.strip()}")
        if result.stderr:
            logger.info(f"OPA stderr: {result.stderr.strip()}")

        if result.returncode == 0:
            logger.info("OPA binary is working correctly")
            return
        else:
            logger.error(f"OPA returned non-zero exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        logger.error("OPA test timed out")
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to execute OPA: {e}")
    except Exception as e:
        logger.error(f"Unexpected error testing OPA: {e}")

    raise RuntimeError("OPA binary is not working")


def validate_environment():
    """Validate environment configuration"""
    required_env_vars = ["PYTHONPATH", "KUBEEYE_DATA_DIR"]

    missing_vars = []
    for var in required_env_vars:
        if var == "KUBEEYE_DATA_DIR":
            if not settings.kubeeye_data_dir:
                missing_vars.append(var)
        elif not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False

    logger.info("Environment variables validation passed")
    return True


def main():
    """Main initialization function"""
    import asyncio

    # Setup logging for init script - use centralized logging config
    from core.logging import get_logger

    logger = get_logger("init")
    logger.info("KubeEye initialization started...")

    async def run_init():
        try:
            # Validate environment
            if not validate_environment():
                sys.exit(1)

            # Ensure data directories
            ensure_data_directories()

            # Ensure database
            await ensure_database()

            # Ensure OPA binary
            ensure_opa_binary()

            logger.info("KubeEye initialization completed!")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            sys.exit(1)

    # Run async command with custom loop factory if uvloop is available
    if uvloop is not None:
        asyncio.run(run_init(), loop_factory=uvloop.new_event_loop)
    else:
        asyncio.run(run_init())


async def initialize(force: bool = False, config_path: Optional[str] = None, verbose: bool = False) -> bool:
    """
    Initialize KubeEye (function for tests)

    Args:
        force: force initialization even if already initialized
        config_path: custom configuration path
        verbose: enable verbose logging

    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        # Setup logging for init script - use centralized logging config
        from core.logging import get_logger

        logger = get_logger("init")
        logger.info("KubeEye initialization started...")

        # Validate environment
        if not validate_environment():
            return False

        # Ensure data directories
        ensure_data_directories()

        # Ensure database
        await ensure_database()

        # Ensure OPA binary
        ensure_opa_binary()

        logger.info("KubeEye initialization completed!")
        return True

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False


if __name__ == "__main__":
    main()
