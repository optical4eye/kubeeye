#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data cleanup manager - automatic cleanup of outdated data to prevent storage overflow
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple
import threading
import time
import atexit

# Get project root directory
ROOT_DIR = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
DATA_DIR = ROOT_DIR

logger = logging.getLogger(__name__)


class DataCleanupManager:
    """Data cleanup manager"""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.cleanup_config = {
            "results": {
                "path": self.data_dir / "results",
                "pattern": "*.json",
                "retention_days": 30,
                "max_files": 1000,
                "enabled": True,
            },
            "logs": {
                "path": self.data_dir / "logs",
                "pattern": "*.log",
                "retention_days": 7,
                "max_size_mb": 100,
                "enabled": True,
            },
            "schedules": {
                "path": self.data_dir / "schedules",
                "pattern": "*.json",
                "retention_days": 90,
                "max_files": 100,
                "enabled": True,
            },
        }

        # Regular cleanup time interval (seconds)
        self.cleanup_interval = 24 * 3600  # Cleanup every 24 hours
        self._cleanup_thread = None
        self._stop_cleanup = False

    def cleanup_by_age(self, dir_path: Path, pattern: str, retention_days: int) -> Tuple[int, int]:
        """Cleanup by file age"""
        if not dir_path.exists():
            return 0, 0

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        total_size = 0

        for file_path in dir_path.glob(pattern):
            try:
                # Get file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if file_mtime < cutoff_date:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    total_size += file_size
                    logger.info(f"Clean up outdated files: {file_path}")

            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")

        return deleted_count, total_size

    def cleanup_by_count(self, dir_path: Path, pattern: str, max_files: int) -> Tuple[int, int]:
        """Cleanup by file count (keep newest files)"""
        if not dir_path.exists():
            return 0, 0

        files = list(dir_path.glob(pattern))
        if len(files) <= max_files:
            return 0, 0

        # Sort by modification time, delete oldest files
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        files_to_delete = files[max_files:]

        deleted_count = 0
        total_size = 0

        for file_path in files_to_delete:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                total_size += file_size
                logger.info(f"Clean up excess files: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")

        return deleted_count, total_size

    def cleanup_by_size(self, dir_path: Path, pattern: str, max_size_mb: int) -> Tuple[int, int]:
        """Cleanup by directory size"""
        if not dir_path.exists():
            return 0, 0

        files = list(dir_path.glob(pattern))
        if not files:
            return 0, 0

        # Calculate total size
        total_size = sum(f.stat().st_size for f in files)
        max_size_bytes = max_size_mb * 1024 * 1024

        if total_size <= max_size_bytes:
            return 0, 0

        # Sort by modification time, delete oldest files until size requirement is met
        files.sort(key=lambda x: x.stat().st_mtime)

        deleted_count = 0
        deleted_size = 0

        for file_path in files:
            if total_size - deleted_size <= max_size_bytes:
                break

            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                deleted_size += file_size
                logger.info(f"Clean up files (size limit): {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")

        return deleted_count, deleted_size

    def cleanup_inspection_results(self) -> Dict:
        """Clean up inspection results"""
        config = self.cleanup_config["results"]
        if not config["enabled"]:
            return {"skipped": True}

        results = {}

        # Cleanup by age
        deleted_count, deleted_size = self.cleanup_by_age(config["path"], config["pattern"], config["retention_days"])
        results["by_age"] = {"count": deleted_count, "size": deleted_size}

        # Cleanup by count
        deleted_count, deleted_size = self.cleanup_by_count(config["path"], config["pattern"], config["max_files"])
        results["by_count"] = {"count": deleted_count, "size": deleted_size}

        return results

    def cleanup_logs(self) -> Dict:
        """Clean up log files"""
        config = self.cleanup_config["logs"]
        if not config["enabled"]:
            return {"skipped": True}

        results = {}

        # Cleanup by age
        deleted_count, deleted_size = self.cleanup_by_age(config["path"], config["pattern"], config["retention_days"])
        results["by_age"] = {"count": deleted_count, "size": deleted_size}

        # Cleanup by size
        deleted_count, deleted_size = self.cleanup_by_size(config["path"], config["pattern"], config["max_size_mb"])
        results["by_size"] = {"count": deleted_count, "size": deleted_size}

        return results

    def cleanup_schedules(self) -> Dict:
        """Clean up scheduled task files"""
        config = self.cleanup_config["schedules"]
        if not config["enabled"]:
            return {"skipped": True}

        results = {}

        # Cleanup by age
        deleted_count, deleted_size = self.cleanup_by_age(config["path"], config["pattern"], config["retention_days"])
        results["by_age"] = {"count": deleted_count, "size": deleted_size}

        return results

    def cleanup_all(self) -> Dict:
        """Perform full cleanup"""
        logger.info("Start data cleanup task")

        results = {
            "timestamp": datetime.now().isoformat(),
            "results": {},
            "logs": {},
            "schedules": {},
        }

        try:
            results["results"] = self.cleanup_inspection_results()
            results["logs"] = self.cleanup_logs()
            results["schedules"] = self.cleanup_schedules()

            logger.info("Data cleanup task completed")

        except Exception as e:
            logger.error(f"Data cleanup task failed: {e}")
            results["error"] = str(e)

        return results

    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        stats = {}

        for name, config in self.cleanup_config.items():
            path = config["path"]
            if not path.exists():
                stats[name] = {"files": 0, "size": 0}
                continue

            files = list(path.glob(config["pattern"]))
            total_size = sum(f.stat().st_size for f in files if f.is_file())

            stats[name] = {
                "files": len(files),
                "size": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
            }

        return stats

    def start_auto_cleanup(self):
        """Start automatic cleanup"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        self._stop_cleanup = False
        self._cleanup_thread = threading.Thread(target=self._auto_cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Automatic data cleanup started")

    def stop_auto_cleanup(self):
        """Stop automatic cleanup"""
        self._stop_cleanup = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Automatic data cleanup stopped")

    def _auto_cleanup_worker(self):
        """Automatic cleanup worker thread"""
        while not self._stop_cleanup:
            try:
                self.cleanup_all()
                # Wait for next cleanup
                for _ in range(self.cleanup_interval):
                    if self._stop_cleanup:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Automatic cleanup exception: {e}")
                time.sleep(60)  # After error wait 1 minute and retry


# Global cleanup manager instance
_cleanup_manager = None


def get_cleanup_manager() -> DataCleanupManager:
    """Get cleanup manager instance"""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = DataCleanupManager()
    return _cleanup_manager


def cleanup_old_data(category: str = "all") -> Dict:
    """Convenient function for cleaning up outdated data"""
    manager = get_cleanup_manager()

    if category == "all":
        return manager.cleanup_all()
    elif category == "results":
        return manager.cleanup_inspection_results()
    elif category == "logs":
        return manager.cleanup_logs()
    elif category == "schedules":
        return manager.cleanup_schedules()
    else:
        raise ValueError(f"Unsupported cleanup category: {category}")


def get_storage_usage() -> Dict:
    """Get storage usage"""
    manager = get_cleanup_manager()
    return manager.get_storage_stats()


# Start automatic cleanup on module import
def _init_auto_cleanup():
    """Initialize automatic cleanup"""
    try:
        manager = get_cleanup_manager()
        manager.start_auto_cleanup()
    except Exception as e:
        logger.warning(f"Failed to start automatic cleanup: {e}")


# Register cleanup on program exit
atexit.register(lambda: get_cleanup_manager().stop_auto_cleanup())

# Start automatic cleanup (can be disabled via environment variable)
if os.getenv("KUBEEYE_DISABLE_AUTO_CLEANUP", "false").lower() != "true":
    _init_auto_cleanup()
