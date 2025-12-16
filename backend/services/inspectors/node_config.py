#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node inspection parallelism configuration management
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class NodeInspectorConfig:
    """Node inspector configuration"""

    # Parallelism management
    max_workers: int = 5  # Maximum number of parallel threads
    timeout: int = 30  # Command execution timeout for one node (seconds)

    # Connection configuration
    connection_timeout: int = 10  # SSH connection timeout (seconds)
    retry_attempts: int = 2  # Number of retry attempts on failed connection
    retry_delay: int = 1  # Interval between retry attempts (seconds)

    # Performance optimization
    enable_connection_pool: bool = True  # Enable connection pool
    pool_size: int = 10  # Connection pool size
    keep_alive: bool = True  # Keep connection alive

    # Logging configuration
    verbose_logging: bool = False  # Verbose logging
    log_command_output: bool = False  # Log command output

    @classmethod
    def from_env(cls) -> "NodeInspectorConfig":
        """Create configuration from environment variables"""
        return cls(
            max_workers=int(os.getenv("NODE_INSPECTOR_MAX_WORKERS", "5")),
            timeout=int(os.getenv("NODE_INSPECTOR_TIMEOUT", "30")),
            connection_timeout=int(os.getenv("NODE_INSPECTOR_CONNECTION_TIMEOUT", "10")),
            retry_attempts=int(os.getenv("NODE_INSPECTOR_RETRY_ATTEMPTS", "2")),
            retry_delay=int(os.getenv("NODE_INSPECTOR_RETRY_DELAY", "1")),
            enable_connection_pool=os.getenv("NODE_INSPECTOR_CONNECTION_POOL", "true").lower() == "true",
            pool_size=int(os.getenv("NODE_INSPECTOR_POOL_SIZE", "10")),
            keep_alive=os.getenv("NODE_INSPECTOR_KEEP_ALIVE", "true").lower() == "true",
            verbose_logging=os.getenv("NODE_INSPECTOR_VERBOSE", "false").lower() == "true",
            log_command_output=os.getenv("NODE_INSPECTOR_LOG_OUTPUT", "false").lower() == "true",
        )

    @classmethod
    def adaptive(cls, node_count: int) -> "NodeInspectorConfig":
        """Adaptive configuration based on node count"""
        if node_count <= 3:
            max_workers = node_count
            timeout = 30
        elif node_count <= 10:
            max_workers = min(5, node_count)
            timeout = 25
        elif node_count <= 20:
            max_workers = min(8, node_count)
            timeout = 20
        else:
            max_workers = min(10, node_count)
            timeout = 15

        return cls(
            max_workers=max_workers,
            timeout=timeout,
            connection_timeout=min(10, timeout // 3),
            retry_attempts=2 if node_count <= 10 else 1,
            verbose_logging=node_count <= 5,  # Enable verbose logging for small node counts
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_workers": self.max_workers,
            "timeout": self.timeout,
            "connection_timeout": self.connection_timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "enable_connection_pool": self.enable_connection_pool,
            "pool_size": self.pool_size,
            "keep_alive": self.keep_alive,
            "verbose_logging": self.verbose_logging,
            "log_command_output": self.log_command_output,
        }

    def validate(self) -> List[str]:
        """Validate configuration"""
        issues = []

        if self.max_workers < 1:
            issues.append("max_workers must be greater than 0")
        if self.max_workers > 20:
            issues.append("max_workers should not exceed 20, may cause resource overload")

        if self.timeout < 5:
            issues.append("timeout should not be less than 5 seconds")
        if self.timeout > 300:
            issues.append("timeout should not exceed 5 minutes")

        if self.connection_timeout < 1:
            issues.append("connection_timeout must be greater than 0")

        if self.retry_attempts < 0:
            issues.append("retry_attempts cannot be less than 0")
        if self.retry_attempts > 5:
            issues.append("retry_attempts should not exceed 5 times")

        return issues
