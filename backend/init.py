#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye initialization script
For initialization work when starting the Docker container
"""

import os
import sys
from pathlib import Path


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
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Ensure directory exists: {directory}")


def validate_environment():
    """Validate environment configuration"""
    required_env_vars = ["PYTHONPATH", "KUBEEYE_DATA_DIR"]

    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")
        return False

    print("Environment variables validation passed")
    return True


def main():
    """Main initialization function"""
    print("KubeEye initialization started...")

    try:
        # Validate environment
        if not validate_environment():
            sys.exit(1)

        # Ensure data directories
        ensure_data_directories()

        print("KubeEye initialization completed!")

    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
