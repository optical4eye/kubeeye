#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye initialization script
For initialization work when starting the Docker container
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Setup logger
logger = logging.getLogger(__name__)


def ensure_data_directories():
    """Ensure data directories exist"""
    data_dir = Path(os.environ.get("KUBEEYE_DATA_DIR", "/app/data"))

    # Create necessary directories
    directories = [
        data_dir / "clusters",
        data_dir / "results",
        data_dir / "logs",
        data_dir / "schedules",
        data_dir / "git_rules",
    ]

    for directory in directories:
        os.makedirs(str(directory), exist_ok=True)
        logger.info(f"Ensure directory exists: {directory}")


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
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False

    logger.info("Environment variables validation passed")
    return True


def main():
    """Main initialization function"""
    # Setup logging for init script
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("KubeEye initialization started...")

    try:
        # Validate environment
        if not validate_environment():
            sys.exit(1)

        # Ensure data directories
        ensure_data_directories()

        # Ensure OPA binary
        ensure_opa_binary()

        logger.info("KubeEye initialization completed!")

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


def initialize(force: bool = False, config_path: Optional[str] = None, verbose: bool = False) -> bool:
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
        # Setup logging for init script
        log_level = logging.INFO if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info("KubeEye initialization started...")

        # Validate environment
        if not validate_environment():
            return False

        # Ensure data directories
        ensure_data_directories()

        # Ensure OPA binary
        ensure_opa_binary()

        logger.info("KubeEye initialization completed!")
        return True

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False


if __name__ == "__main__":
    main()
