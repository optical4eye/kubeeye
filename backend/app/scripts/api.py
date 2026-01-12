#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main API entry point - imports from controllers modules
"""

# Performance optimization: use uvloop for better asyncio performance
try:
    import uvloop
    import asyncio

    # Use loop_factory instead of set_event_loop_policy (Python 3.14+)
    # This will be used by uvicorn.run() via custom_loop_factory
except ImportError:
    uvloop = None  # uvloop not available, use default asyncio

from api.main import app
import sys
import argparse

# Initialize logging
from core.logging import setup_logging
from core.config.settings import settings
from loguru import logger

# Log current state before setup
logger.info(
    f"Initializing logging: current level={logger.level}, configured KUBEEYE_LOG_LEVEL={settings.kubeeye_log_level}"
)

# Setup logging with configured level
setup_logging(log_level=settings.kubeeye_log_level)

# Log after setup
logger.info(f"Logging initialized with level: {settings.kubeeye_log_level}")


def custom_loop_factory():
    """Custom event loop factory for Python 3.14 optimizations"""
    # Use uvloop if available, otherwise use default asyncio
    if uvloop is not None:
        loop = uvloop.new_event_loop()
    else:
        loop = asyncio.new_event_loop()

    # Enable eager task factory for better performance in Python 3.14+
    try:
        loop.set_task_factory(asyncio.eager_task_factory)
    except AttributeError:
        # eager_task_factory not available in older Python versions
        pass
    return loop


def main():
    """Main function for API script (for tests)"""
    parser = argparse.ArgumentParser(description="KubeEye API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        parser.print_help()
        return

    try:
        import uvicorn

        # Use custom loop factory for Python 3.14 optimizations
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            loop_factory=custom_loop_factory,
            log_config=None,
            access_log=False,
        )
    except ImportError:
        print("uvicorn not available, API server cannot start")
        sys.exit(1)


if __name__ == "__main__":
    main()
