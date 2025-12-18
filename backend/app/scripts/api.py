#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main API entry point - imports from controllers modules
"""

from api.main import app
import sys
import argparse


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

        uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    except ImportError:
        print("uvicorn not available, API server cannot start")
        sys.exit(1)


if __name__ == "__main__":
    main()
