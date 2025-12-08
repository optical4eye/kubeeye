#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye automatic cleanup script for old reports
Can be executed on schedule via cron
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add root directory to path
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Cleanup functions (copied for autonomy)
import json
from pathlib import Path
from datetime import datetime, timedelta

CONFIG_FILE = Path(__file__).parent / "data" / "cleanup_config.json"
DEFAULT_RETENTION_DAYS = 14
DEFAULT_AUTO_CLEANUP = False

# Environment variable for retention days
ENV_RETENTION_DAYS = "KUBEYE_REPORT_RETENTION_DAYS"

def load_cleanup_config() -> dict:
    """Load cleanup configuration"""
    # Check environment variable first
    env_retention = os.getenv(ENV_RETENTION_DAYS)
    if env_retention:
        try:
            retention_days = int(env_retention)
            if retention_days > 0:
                return {
                    'retention_days': retention_days,
                    'source': 'env'
                }
        except ValueError:
            pass

    # Fall back to config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config['source'] = 'file'
                return config
        except Exception:
            pass

    return {
        'retention_days': DEFAULT_RETENTION_DAYS,
        'source': 'default'
    }

def save_cleanup_config(config: dict):
    """Save cleanup configuration"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def cleanup_old_reports(retention_days: int) -> tuple[int, int]:
    """Clean up old reports older than retention_days days

    Returns:
        tuple: (deleted_files, freed_space_in_bytes)
    """
    if retention_days <= 0:
        return 0, 0

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    results_dir = Path(__file__).parent / "data" / "results"

    if not results_dir.exists():
        return 0, 0

    deleted_count = 0
    freed_space = 0

    for file_path in results_dir.glob("*.json"):
        try:
            # Check file modification date
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
    print("Starting KubeEye reports cleanup...")

    try:
        # Load configuration
        config = load_cleanup_config()
        retention_days = config.get('retention_days', DEFAULT_RETENTION_DAYS)
        print(f"Retention period: {retention_days} days")

        # Execute cleanup
        deleted_count, freed_space = cleanup_old_reports(retention_days)

        # Display results
        if deleted_count > 0:
            freed_mb = freed_space / (1024 * 1024)
            print(f"Deleted {deleted_count} files, freed {freed_mb:.1f} MB")
        else:
            print("No files found for deletion")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)


def main():
    """Main function for running from command line"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
KubeEye - cleanup of old reports

Usage:
    python3 cleanup_reports.py          # Run cleanup
    python3 cleanup_reports.py --help    # Show this help

Example:
    cd /path/to/kubeeye
    python3 cleanup_reports.py
            """)
            return

    run_cleanup()


if __name__ == "__main__":
    main()