#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for data cleanup manager
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from infrastructure.common.data_cleanup import (
    DataCleanupManager,
    get_cleanup_manager,
    cleanup_old_data,
    get_storage_usage,
)


class TestDataCleanupManager:
    """Test cases for DataCleanupManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def cleanup_manager(self, temp_dir):
        """Create DataCleanupManager instance with temporary directory"""
        with patch("app.infrastructure.common.data_cleanup.DATA_DIR", temp_dir):
            manager = DataCleanupManager()
            # Update paths to use temp directory
            for config in manager.cleanup_config.values():
                config["path"] = temp_dir / config["path"].name
            yield manager

    def test_init(self, cleanup_manager):
        """Test DataCleanupManager initialization"""
        assert cleanup_manager.cleanup_interval == 24 * 3600
        assert cleanup_manager._cleanup_thread is None
        assert cleanup_manager._stop_cleanup is False
        assert "results" in cleanup_manager.cleanup_config
        assert "logs" in cleanup_manager.cleanup_config
        assert "schedules" in cleanup_manager.cleanup_config

    def test_cleanup_by_age_no_directory(self, cleanup_manager):
        """Test cleanup_by_age with non-existent directory"""
        non_existent_dir = Path("/non/existent/directory")
        deleted_count, total_size = cleanup_manager.cleanup_by_age(non_existent_dir, "*.json", 30)

        assert deleted_count == 0
        assert total_size == 0

    def test_cleanup_by_age_with_files(self, cleanup_manager, temp_dir):
        """Test cleanup_by_age with files"""
        # Create test directory and files
        test_dir = temp_dir / "test_age"
        test_dir.mkdir()

        # Create old file (should be deleted)
        old_file = test_dir / "old.json"
        old_file.write_text("old data")

        # Create new file (should be kept)
        new_file = test_dir / "new.json"
        new_file.write_text("new data")

        # Set old file modification time to 40 days ago
        old_time = time.time() - (40 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        # Run cleanup with 30 days retention
        deleted_count, total_size = cleanup_manager.cleanup_by_age(test_dir, "*.json", 30)

        assert deleted_count == 1
        assert total_size > 0
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_by_age_no_files_to_delete(self, cleanup_manager, temp_dir):
        """Test cleanup_by_age with no files to delete"""
        # Create test directory and recent file
        test_dir = temp_dir / "test_recent"
        test_dir.mkdir()

        recent_file = test_dir / "recent.json"
        recent_file.write_text("recent data")

        # Run cleanup with 30 days retention
        deleted_count, total_size = cleanup_manager.cleanup_by_age(test_dir, "*.json", 30)

        assert deleted_count == 0
        assert total_size == 0
        assert recent_file.exists()

    def test_cleanup_by_count_no_directory(self, cleanup_manager):
        """Test cleanup_by_count with non-existent directory"""
        non_existent_dir = Path("/non/existent/directory")
        deleted_count, total_size = cleanup_manager.cleanup_by_count(non_existent_dir, "*.json", 10)

        assert deleted_count == 0
        assert total_size == 0

    def test_cleanup_by_count_with_files(self, cleanup_manager, temp_dir):
        """Test cleanup_by_count with files"""
        # Create test directory and files
        test_dir = temp_dir / "test_count"
        test_dir.mkdir()

        # Create 5 files
        files = []
        for i in range(5):
            file_path = test_dir / f"file_{i}.json"
            file_path.write_text(f"data {i}")
            files.append(file_path)

            # Set different modification times (older files first)
            file_time = time.time() - ((5 - i) * 24 * 3600)  # 5, 4, 3, 2, 1 days ago
            os.utime(file_path, (file_time, file_time))

        # Run cleanup with max 3 files (should delete 2 oldest)
        deleted_count, total_size = cleanup_manager.cleanup_by_count(test_dir, "*.json", 3)

        assert deleted_count == 2
        assert total_size > 0
        assert not files[0].exists()  # Oldest deleted
        assert not files[1].exists()  # Second oldest deleted
        assert files[2].exists()  # Third oldest kept
        assert files[3].exists()  # Fourth kept
        assert files[4].exists()  # Newest kept

    def test_cleanup_by_count_no_files_to_delete(self, cleanup_manager, temp_dir):
        """Test cleanup_by_count with no files to delete"""
        # Create test directory and 2 files
        test_dir = temp_dir / "test_few"
        test_dir.mkdir()

        for i in range(2):
            file_path = test_dir / f"file_{i}.json"
            file_path.write_text(f"data {i}")

        # Run cleanup with max 5 files (should delete none)
        deleted_count, total_size = cleanup_manager.cleanup_by_count(test_dir, "*.json", 5)

        assert deleted_count == 0
        assert total_size == 0

    def test_cleanup_by_size_no_directory(self, cleanup_manager):
        """Test cleanup_by_size with non-existent directory"""
        non_existent_dir = Path("/non/existent/directory")
        deleted_count, total_size = cleanup_manager.cleanup_by_size(non_existent_dir, "*.json", 10)

        assert deleted_count == 0
        assert total_size == 0

    def test_cleanup_by_size_with_files(self, cleanup_manager, temp_dir):
        """Test cleanup_by_size with files"""
        # Create test directory and files
        test_dir = temp_dir / "test_size"
        test_dir.mkdir()

        # Create files with different sizes
        files = []
        sizes = [1000, 2000, 3000, 4000, 5000]  # Total 15000 bytes

        for i, size in enumerate(sizes):
            file_path = test_dir / f"file_{i}.json"
            file_path.write_text("x" * size)
            files.append(file_path)

            # Set different modification times (older files first)
            file_time = time.time() - ((5 - i) * 24 * 3600)  # 5, 4, 3, 2, 1 days ago
            os.utime(file_path, (file_time, file_time))

        # Run cleanup with max 10000 bytes (should delete oldest files until under limit)
        deleted_count, total_size = cleanup_manager.cleanup_by_size(test_dir, "*.json", 0.01)  # 0.01 MB = 10240 bytes

        assert deleted_count == 3  # Should delete 3 oldest files (1000 + 2000 + 3000 = 6000 bytes)
        assert total_size == 6000  # Total size of deleted files
        assert not files[0].exists()  # Oldest deleted
        assert not files[1].exists()  # Second oldest deleted
        assert not files[2].exists()  # Third oldest deleted
        assert files[3].exists()  # Fourth kept
        assert files[4].exists()  # Newest kept

    def test_cleanup_by_size_no_files_to_delete(self, cleanup_manager, temp_dir):
        """Test cleanup_by_size with no files to delete"""
        # Create test directory and small file
        test_dir = temp_dir / "test_small"
        test_dir.mkdir()

        file_path = test_dir / "small.json"
        file_path.write_text("x" * 100)  # 100 bytes

        # Run cleanup with max 1 MB (should delete none)
        deleted_count, total_size = cleanup_manager.cleanup_by_size(test_dir, "*.json", 1)

        assert deleted_count == 0
        assert total_size == 0

    def test_cleanup_inspection_results_disabled(self, cleanup_manager):
        """Test cleanup_inspection_results when disabled"""
        cleanup_manager.cleanup_config["results"]["enabled"] = False

        result = cleanup_manager.cleanup_inspection_results()

        assert result == {"skipped": True}

    def test_cleanup_inspection_results_enabled(self, cleanup_manager, temp_dir):
        """Test cleanup_inspection_results when enabled"""
        # Create test directory and files
        results_dir = temp_dir / "results"
        results_dir.mkdir()

        # Create old file
        old_file = results_dir / "old.json"
        old_file.write_text("old data")
        old_time = time.time() - (40 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        result = cleanup_manager.cleanup_inspection_results()

        assert "by_age" in result
        assert "by_count" in result
        assert result["by_age"]["count"] == 1
        assert result["by_age"]["size"] > 0

    def test_cleanup_logs_disabled(self, cleanup_manager):
        """Test cleanup_logs when disabled"""
        cleanup_manager.cleanup_config["logs"]["enabled"] = False

        result = cleanup_manager.cleanup_logs()

        assert result == {"skipped": True}

    def test_cleanup_logs_enabled(self, cleanup_manager, temp_dir):
        """Test cleanup_logs when enabled"""
        # Create test directory and files
        logs_dir = temp_dir / "logs"
        logs_dir.mkdir()

        # Create old file
        old_file = logs_dir / "old.log"
        old_file.write_text("old log data")
        old_time = time.time() - (10 * 24 * 3600)  # 10 days ago
        os.utime(old_file, (old_time, old_time))

        result = cleanup_manager.cleanup_logs()

        assert "by_age" in result
        assert "by_size" in result
        assert result["by_age"]["count"] == 1
        assert result["by_age"]["size"] > 0

    def test_cleanup_schedules_disabled(self, cleanup_manager):
        """Test cleanup_schedules when disabled"""
        cleanup_manager.cleanup_config["schedules"]["enabled"] = False

        result = cleanup_manager.cleanup_schedules()

        assert result == {"skipped": True}

    def test_cleanup_schedules_enabled(self, cleanup_manager, temp_dir):
        """Test cleanup_schedules when enabled"""
        # Create test directory and files
        schedules_dir = temp_dir / "schedules"
        schedules_dir.mkdir()

        # Create old file
        old_file = schedules_dir / "old.json"
        old_file.write_text("old schedule data")
        old_time = time.time() - (100 * 24 * 3600)  # 100 days ago
        os.utime(old_file, (old_time, old_time))

        result = cleanup_manager.cleanup_schedules()

        assert "by_age" in result
        assert result["by_age"]["count"] == 1
        assert result["by_age"]["size"] > 0

    def test_cleanup_all(self, cleanup_manager, temp_dir):
        """Test cleanup_all method"""
        # Create test directories and files
        for dir_name in ["results", "logs", "schedules"]:
            dir_path = temp_dir / dir_name
            dir_path.mkdir()

            # Create old file
            old_file = dir_path / "old.json" if dir_name != "logs" else dir_path / "old.log"
            old_file.write_text("old data")
            old_time = time.time() - (40 * 24 * 3600)
            os.utime(old_file, (old_time, old_time))

        result = cleanup_manager.cleanup_all()

        assert "timestamp" in result
        assert "results" in result
        assert "logs" in result
        assert "schedules" in result
        assert "error" not in result

    def test_cleanup_all_with_error(self, cleanup_manager):
        """Test cleanup_all with error"""
        # Mock cleanup method to raise exception
        with patch.object(cleanup_manager, "cleanup_inspection_results", side_effect=Exception("Test error")):
            result = cleanup_manager.cleanup_all()

            assert "error" in result
            assert result["error"] == "Test error"

    def test_get_storage_stats(self, cleanup_manager, temp_dir):
        """Test get_storage_stats method"""
        # Create test directories and files
        for dir_name in ["results", "logs", "schedules"]:
            dir_path = temp_dir / dir_name
            dir_path.mkdir()

            # Create file with content
            file_name = "test.json" if dir_name != "logs" else "test.log"
            file_path = dir_path / file_name
            file_path.write_text("x" * 1000)  # 1000 bytes

        stats = cleanup_manager.get_storage_stats()

        assert "results" in stats
        assert "logs" in stats
        assert "schedules" in stats

        for stat_name in ["results", "logs", "schedules"]:
            assert stats[stat_name]["files"] == 1
            assert stats[stat_name]["size"] == 1000
            expected_mb = round(1000 / (1024 * 1024), 2)
            assert abs(stats[stat_name]["size_mb"] - expected_mb) < 0.01

    def test_get_storage_stats_no_directory(self, cleanup_manager):
        """Test get_storage_stats with non-existent directories"""
        stats = cleanup_manager.get_storage_stats()

        for stat_name in ["results", "logs", "schedules"]:
            assert stats[stat_name]["files"] == 0
            assert stats[stat_name]["size"] == 0
            assert "size_mb" in stats[stat_name]
            assert stats[stat_name]["size_mb"] == 0

    def test_start_auto_cleanup(self, cleanup_manager):
        """Test start_auto_cleanup method"""
        # Mock the thread to avoid actually starting it
        with patch("threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            cleanup_manager.start_auto_cleanup()

            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            assert cleanup_manager._stop_cleanup is False

    def test_start_auto_cleanup_already_running(self, cleanup_manager):
        """Test start_auto_cleanup when already running"""
        # Mock thread that appears to be running
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        cleanup_manager._cleanup_thread = mock_thread

        cleanup_manager.start_auto_cleanup()

        # Should not start new thread
        assert cleanup_manager._cleanup_thread == mock_thread

    def test_stop_auto_cleanup(self, cleanup_manager):
        """Test stop_auto_cleanup method"""
        # Mock thread
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        cleanup_manager._cleanup_thread = mock_thread

        cleanup_manager.stop_auto_cleanup()

        assert cleanup_manager._stop_cleanup is True
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_stop_auto_cleanup_no_thread(self, cleanup_manager):
        """Test stop_auto_cleanup with no thread running"""
        cleanup_manager._cleanup_thread = None

        # Should not raise exception
        cleanup_manager.stop_auto_cleanup()

        assert cleanup_manager._stop_cleanup is True

    def test_auto_cleanup_worker(self, cleanup_manager):
        """Test _auto_cleanup_worker method"""
        # Mock cleanup_all and sleep
        with patch.object(cleanup_manager, "cleanup_all") as mock_cleanup, patch("time.sleep") as mock_sleep:

            # Set stop flag after first cleanup
            def side_effect(*args, **kwargs):
                cleanup_manager._stop_cleanup = True

            mock_sleep.side_effect = side_effect

            cleanup_manager._auto_cleanup_worker()

            mock_cleanup.assert_called_once()

    def test_auto_cleanup_worker_with_error(self, cleanup_manager):
        """Test _auto_cleanup_worker with error"""
        # Mock cleanup_all to raise exception
        with patch.object(cleanup_manager, "cleanup_all", side_effect=Exception("Test error")), patch(
            "time.sleep"
        ) as mock_sleep:

            # Set stop flag after first sleep
            def side_effect(*args, **kwargs):
                cleanup_manager._stop_cleanup = True

            mock_sleep.side_effect = side_effect

            # Should not raise exception
            cleanup_manager._auto_cleanup_worker()


class TestModuleFunctions:
    """Test cases for module-level functions"""

    def test_get_cleanup_manager(self):
        """Test get_cleanup_manager function"""
        # Clear global manager
        import app.infrastructure.common.data_cleanup as data_cleanup

        data_cleanup._cleanup_manager = None

        manager = get_cleanup_manager()

        assert isinstance(manager, DataCleanupManager)

        # Second call should return same instance
        manager2 = get_cleanup_manager()
        assert manager is manager2

    def test_cleanup_old_data_all(self):
        """Test cleanup_old_data with 'all' category"""
        with patch("infrastructure.common.data_cleanup.get_cleanup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.cleanup_all.return_value = {"test": "result"}

            result = cleanup_old_data("all")

            # Verify the manager was retrieved and method was called
            mock_get_manager.assert_called_once()
            mock_manager.cleanup_all.assert_called_once()
            assert result == {"test": "result"}

    def test_cleanup_old_data_results(self):
        """Test cleanup_old_data with 'results' category"""
        with patch("infrastructure.common.data_cleanup.get_cleanup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.cleanup_inspection_results.return_value = {"test": "result"}

            result = cleanup_old_data("results")

            # Verify the manager was retrieved and method was called
            mock_get_manager.assert_called_once()
            mock_manager.cleanup_inspection_results.assert_called_once()
            assert result == {"test": "result"}

    def test_cleanup_old_data_logs(self):
        """Test cleanup_old_data with 'logs' category"""
        with patch("infrastructure.common.data_cleanup.get_cleanup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.cleanup_logs.return_value = {"test": "result"}

            result = cleanup_old_data("logs")

            # Verify the manager was retrieved and method was called
            mock_get_manager.assert_called_once()
            mock_manager.cleanup_logs.assert_called_once()
            assert result == {"test": "result"}

    def test_cleanup_old_data_schedules(self):
        """Test cleanup_old_data with 'schedules' category"""
        with patch("infrastructure.common.data_cleanup.get_cleanup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.cleanup_schedules.return_value = {"test": "result"}

            result = cleanup_old_data("schedules")

            # Verify the manager was retrieved and method was called
            mock_get_manager.assert_called_once()
            mock_manager.cleanup_schedules.assert_called_once()
            assert result == {"test": "result"}

    def test_cleanup_old_data_invalid_category(self):
        """Test cleanup_old_data with invalid category"""
        with pytest.raises(ValueError) as exc_info:
            cleanup_old_data("invalid")

        assert "Unsupported cleanup category: invalid" in str(exc_info.value)

    def test_get_storage_usage(self):
        """Test get_storage_usage function"""
        with patch("infrastructure.common.data_cleanup.get_cleanup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.get_storage_stats.return_value = {"test": "stats"}

            result = get_storage_usage()

            # Verify the manager was retrieved and method was called
            mock_get_manager.assert_called_once()
            mock_manager.get_storage_stats.assert_called_once()
            assert result == {"test": "stats"}
