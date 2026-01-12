#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retry utilities for handling transient failures
"""

import asyncio
from functools import wraps
from typing import Callable, Any, Optional
from core.common.exceptions import DatabaseError, NetworkError

from core.logging import get_logger

logger = get_logger(__name__)


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (DatabaseError, NetworkError, ConnectionError, OSError),
):
    """
    Decorator for retrying operations on failure

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to retry on
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator


def retry_sync_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (DatabaseError, NetworkError, ConnectionError, OSError),
):
    """
    Synchronous version of retry decorator
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s..."
                        )
                        import time

                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator
