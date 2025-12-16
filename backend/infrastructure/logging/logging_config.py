#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced logging configuration module for unified project log management
"""

import os
import logging
from pathlib import Path
from typing import Optional

# Import enhanced logging
from infrastructure.logging.enhanced_logging import (
    setup_logging,
    get_error_summary,
)

# Data directory definition
DATA_DIR = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
LOGS_DIR = DATA_DIR / "logs"

# Ensure log directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Default log file path
DEFAULT_LOG_FILE = LOGS_DIR / "kubeeye.log"

# Log level mapping (for backward compatibility)
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def setup_logger(
    name: str,
    level: str = "info",
    log_file: Optional[Path] = None,
    log_format: str = None,  # Kept for backward compatibility
) -> logging.Logger:
    """
    Set up logger (backward compatibility wrapper)

    Args:
        name: Logger name
        level: Log level
        log_file: Log file path, if None then use default path
        log_format: Log format (ignored, using structured logging)

    Returns:
        Configured logger
    """
    # Use enhanced logging setup
    logger = setup_logging(
        log_level=level.upper(),
        log_file=str(log_file) if log_file else str(DEFAULT_LOG_FILE),
        enable_structured=True,
        enable_console=True,
    )

    # Return named logger
    return logging.getLogger(name)


# Create default project logger using enhanced logging
project_logger = setup_logging(
    log_level="INFO",
    log_file=str(DEFAULT_LOG_FILE),
    enable_structured=True,
    enable_console=True,
)


def get_logger(module_name: str) -> logging.Logger:
    """
    Get logger for specified module

    Args:
        module_name: Module name

    Returns:
        Configured module logger
    """
    return logging.getLogger(f"kubeeye.{module_name}")


def get_system_health() -> dict:
    """
    Get system health information including error statistics

    Returns:
        Health information dictionary
    """
    return {
        "logging": {
            "error_summary": get_error_summary(),
            "log_file": str(DEFAULT_LOG_FILE),
            "log_directory": str(LOGS_DIR),
        }
    }


# Set log levels for third-party libraries
logging.getLogger("asyncssh").setLevel(logging.WARNING)
logging.getLogger("kubernetes").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
