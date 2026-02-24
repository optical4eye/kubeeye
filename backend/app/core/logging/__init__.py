#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified logging module - single entry point for all logging functionality
Provides access to both basic and enhanced logging features
"""

# Import all logging functionality from enhanced_logging module
from .enhanced_logging import (
    setup_logging,
    get_error_summary,
    log_execution_time,
    log_api_request,
    ErrorBoundary,
    ErrorTracker,
    error_tracker,
    StructuredFormatter,
    structured_formatter,
    colored_formatter,
    setup_performance_monitoring,
    disable_performance_monitoring,
    get_logger,
    get_system_health,
    LOG_LEVELS,
    request_id,
    user_id,
    cluster_name,
    resource_name,
    resource_type,
    resource_id,
    client_ip,
    client_user_agent,
)

__all__ = [
    # Basic logging
    "get_logger",
    "get_system_health",
    "LOG_LEVELS",
    # Enhanced logging
    "setup_logging",
    "get_error_summary",
    "log_execution_time",
    "log_api_request",
    "ErrorBoundary",
    "ErrorTracker",
    "error_tracker",
    "StructuredFormatter",
    "structured_formatter",
    "colored_formatter",
    "setup_performance_monitoring",
    "disable_performance_monitoring",
    # Context variables
    "request_id",
    "user_id",
    "cluster_name",
    "resource_name",
    "resource_type",
    "resource_id",
    "client_ip",
    "client_user_agent",
]
