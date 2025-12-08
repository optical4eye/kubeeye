#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging configuration module for unified project log management
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

# Data directory definition
DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = DATA_DIR / "logs"

# Ensure log directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Default log file path
DEFAULT_LOG_FILE = LOGS_DIR / "kubeeye.log"

# Log level mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logger(name: str, level: str = "info",
                log_file: Optional[Path] = None,
                log_format: str = DEFAULT_LOG_FORMAT) -> logging.Logger:
    """
    Set up logger

    Args:
        name: Logger name
        level: Log level
        log_file: Log file path, if None then use default path
        log_format: Log format

    Returns:
        Configured logger
    """
    # Get log level
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create file handler
    if log_file is None:
        log_file = DEFAULT_LOG_FILE

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Create default project logger
project_logger = setup_logger("kubeeye")

def get_logger(module_name: str) -> logging.Logger:
    """
    Get logger for specified module

    Args:
        module_name: Module name

    Returns:
        Configured module logger
    """
    return logging.getLogger(f"kubeeye.{module_name}")

# Set log levels for third-party libraries
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("kubernetes").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("streamlit").setLevel(logging.WARNING)
