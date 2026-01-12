#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance metrics and monitoring utilities
"""

import asyncio
import time
import inspect
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import asynccontextmanager

from core.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Simple metrics collector for performance monitoring"""

    def __init__(self):
        self.metrics = {}
        self.counters = {}

    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter metric"""
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value

    def record_timing(self, name: str, duration: float):
        """Record timing metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(duration)

        # Keep only last 100 measurements
        if len(self.metrics[name]) > 100:
            self.metrics[name] = self.metrics[name][-100:]

    def get_average_timing(self, name: str) -> Optional[float]:
        """Get average timing for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return sum(self.metrics[name]) / len(self.metrics[name])

    def get_counter(self, name: str) -> int:
        """Get counter value"""
        return self.counters.get(name, 0)

    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics statistics"""
        stats = {}
        for name, timings in self.metrics.items():
            if timings:
                stats[f"{name}_avg"] = sum(timings) / len(timings)
                stats[f"{name}_min"] = min(timings)
                stats[f"{name}_max"] = max(timings)
                stats[f"{name}_count"] = len(timings)

        stats.update(self.counters)
        return stats

    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()


# Global metrics collector
metrics = MetricsCollector()


def time_operation(operation_name: str):
    """Decorator to time operations"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_timing(operation_name, duration)
                logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_timing(f"{operation_name}_error", duration)
                logger.error(f"Operation {operation_name} failed after {duration:.3f}s: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_timing(operation_name, duration)
                logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_timing(f"{operation_name}_error", duration)
                logger.error(f"Operation {operation_name} failed after {duration:.3f}s: {e}")
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def measure_async_operation(operation_name: str):
    """Async context manager to measure operation duration"""
    start_time = time.time()
    try:
        yield
        duration = time.time() - start_time
        metrics.record_timing(operation_name, duration)
        logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_timing(f"{operation_name}_error", duration)
        logger.error(f"Operation {operation_name} failed after {duration:.3f}s: {e}")
        raise


def count_requests(endpoint: str):
    """Decorator to count API requests"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics.increment_counter(f"requests_{endpoint}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def log_performance_stats():
    """Log current performance statistics"""
    stats = metrics.get_stats()
    if stats:
        logger.info("Performance metrics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
    else:
        logger.info("No performance metrics available")
