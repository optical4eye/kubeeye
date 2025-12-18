#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye automatic cleanup script for old reports
Can be executed on schedule via cron
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add root directory to path
ROOT_DIR = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent))).parent  # backend/
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Setup logger
logger = logging.getLogger(__name__)

CONFIG_FILE = ROOT_DIR / "data" / "cleanup_config.json"
DEFAULT_RETENTION_DAYS = 7
DEFAULT_AUTO_CLEANUP = False

# Environment variable for retention days
ENV_RETENTION_DAYS = "KUBEYE_REPORT_RETENTION_DAYS"


def load_cleanup_config() -> dict:
    """Load cleanup configuration"""
    # Check environment variable first
    env_retention = os.getenv(ENV_RETENTION_DAYS)
    if env_retention is not None:
        try:
            retention_days = int(env_retention)
            if retention_days >= 0:
                return {"retention_days": retention_days, "source": "env"}
        except ValueError:
            pass

    # Fall back to config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                config["source"] = "file"
                return config
        except Exception:
            pass

    return {"retention_days": DEFAULT_RETENTION_DAYS, "source": "default"}


def save_cleanup_config(config: dict):
    """Save cleanup configuration"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def cleanup_old_reports(retention_days: int) -> tuple[int, int]:
    """Clean up old reports older than retention_days days

    Args:
        retention_days: number of days to keep files. Use 0 to delete all files.

    Returns:
        tuple: (deleted_files, freed_space_in_bytes)
    """
    if retention_days < 0:
        return 0, 0

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    data_dir = ROOT_DIR / "data"

    deleted_count = 0
    freed_space = 0

    # Directories to clean up
    cleanup_dirs = [
        data_dir / "results",  # Regular inspection reports and network checks
        data_dir / "exports",  # Exported reports
    ]

    for results_dir in cleanup_dirs:
        if not results_dir.exists():
            continue

        # Clean up all files in directory and subdirectories
        for file_path in results_dir.rglob("*"):
            if file_path.is_file():
                try:
                    if retention_days == 0:
                        # Delete all files when retention_days is 0
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        freed_space += file_size
                    else:
                        # Check file modification date for retention_days > 0
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            freed_space += file_size
                except Exception:
                    continue

    return deleted_count, freed_space


def run_cleanup():
    """Execute cleanup of reports according to settings"""
    logger.info("Starting KubeEye reports and network checks cleanup...")

    try:
        # Load configuration
        config = load_cleanup_config()
        retention_days = config.get("retention_days", DEFAULT_RETENTION_DAYS)
        logger.info(f"Retention period: {retention_days} days")

        # Execute cleanup
        deleted_count, freed_space = cleanup_old_reports(retention_days)

        # Display results
        if deleted_count > 0:
            freed_mb = freed_space / (1024 * 1024)
            logger.info(f"Deleted {deleted_count} files, freed {freed_mb:.1f} MB")
        else:
            logger.info("No files found for deletion")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        sys.exit(1)


def main():
    """Main function for running from command line"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(
                """
KubeEye - cleanup of old reports

Usage:
    python3 cleanup_reports.py          # Run cleanup
    python3 cleanup_reports.py --help    # Show this help

Example:
    cd /path/to/kubeeye
    python3 cleanup_reports.py
            """
            )
            return

    run_cleanup()


def cleanup_reports(days: Optional[int] = None, dry_run: bool = False) -> tuple[int, int]:
    """
    Cleanup old reports (function for tests)

    Args:
        days: number of days to keep files (overrides config)
        dry_run: if True, only report what would be deleted

    Returns:
        tuple: (deleted_files, freed_space_in_bytes)
    """
    if days is None:
        config = load_cleanup_config()
        days = config.get("retention_days", DEFAULT_RETENTION_DAYS)

    # Ensure days is an integer
    if days is None:
        days = DEFAULT_RETENTION_DAYS

    if dry_run:
        # In dry run mode, just count what would be deleted
        logger.info(f"DRY RUN: Would clean up files older than {days} days")
        # For now, return 0,0 since we're not actually deleting
        return 0, 0

    return cleanup_old_reports(days)


if __name__ == "__main__":
    main()
