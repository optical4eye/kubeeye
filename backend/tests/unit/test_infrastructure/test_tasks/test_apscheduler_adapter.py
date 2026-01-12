#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for APSchedulerAdapter
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from infra.tasks.apscheduler_adapter import APSchedulerAdapter


class TestAPSchedulerAdapter:
    """Test cases for APSchedulerAdapter"""

    @pytest.fixture
    def scheduler_adapter(self):
        """Create APSchedulerAdapter instance"""
        return APSchedulerAdapter()

    @pytest.mark.asyncio
    async def test_start_success(self, scheduler_adapter):
        """Test successful scheduler start"""
        with patch.object(scheduler_adapter.scheduler, "start") as mock_start:
            result = await scheduler_adapter.start()
            assert result is True
            mock_start.assert_called_once()
            assert scheduler_adapter._running is True

    @pytest.mark.asyncio
    async def test_start_already_running(self, scheduler_adapter):
        """Test start when already running"""
        scheduler_adapter._running = True
        result = await scheduler_adapter.start()
        assert result is True

    @pytest.mark.asyncio
    async def test_start_exception(self, scheduler_adapter):
        """Test start with exception"""
        with patch.object(scheduler_adapter.scheduler, "start", side_effect=Exception("Start error")):
            result = await scheduler_adapter.start()
            assert result is False
            assert scheduler_adapter._running is False

    @pytest.mark.asyncio
    async def test_stop_success(self, scheduler_adapter):
        """Test successful scheduler stop"""
        scheduler_adapter._running = True
        with patch.object(scheduler_adapter.scheduler, "shutdown") as mock_shutdown:
            result = await scheduler_adapter.stop()
            assert result is True
            mock_shutdown.assert_called_once_with(wait=True)
            assert scheduler_adapter._running is False

    @pytest.mark.asyncio
    async def test_stop_not_running(self, scheduler_adapter):
        """Test stop when not running"""
        result = await scheduler_adapter.stop()
        assert result is True

    @pytest.mark.asyncio
    async def test_stop_exception(self, scheduler_adapter):
        """Test stop with exception"""
        scheduler_adapter._running = True
        with patch.object(scheduler_adapter.scheduler, "shutdown", side_effect=Exception("Stop error")):
            result = await scheduler_adapter.stop()
            assert result is False
            assert scheduler_adapter._running is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cron_expr",
        [
            "0 0 * * *",  # Daily at midnight
            "*/15 * * * *",  # Every 15 minutes
            "0 9-17 * * 1-5",  # Business hours weekdays
            "0 0 1 * *",  # First day of month
        ],
    )
    async def test_add_job_cron_success(self, scheduler_adapter, cron_expr):
        """Test successful cron job addition with various cron expressions"""

        async def dummy_func():
            pass

        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=None), patch.object(
            scheduler_adapter.scheduler, "remove_job"
        ), patch.object(scheduler_adapter.scheduler, "add_job") as mock_add_job:

            result = await scheduler_adapter.add_job(
                job_id="test_job", func=dummy_func, trigger="cron", cron_expr=cron_expr
            )

            assert result is True
            mock_add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_job_cron_invalid_expression(self, scheduler_adapter):
        """Test cron job with invalid expression"""

        async def dummy_func():
            pass

        result = await scheduler_adapter.add_job(
            job_id="test_job", func=dummy_func, trigger="cron", cron_expr="invalid"
        )

        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "run_date",
        [
            "2024-01-01T00:00:00",
            "2025-12-31T23:59:59",
            "2024-06-15T12:30:45",
        ],
    )
    async def test_add_job_date_success(self, scheduler_adapter, run_date):
        """Test successful date job addition with various dates"""

        async def dummy_func():
            pass

        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=None), patch.object(
            scheduler_adapter.scheduler, "remove_job"
        ), patch.object(scheduler_adapter.scheduler, "add_job") as mock_add_job:

            result = await scheduler_adapter.add_job(
                job_id="test_job", func=dummy_func, trigger="date", run_date=run_date
            )

            assert result is True
            mock_add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_job_date_no_run_date(self, scheduler_adapter):
        """Test date job without run_date"""

        async def dummy_func():
            pass

        result = await scheduler_adapter.add_job(job_id="test_job", func=dummy_func, trigger="date")

        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "interval_params,expected",
        [
            ({"hours": 1}, True),
            ({"minutes": 30}, True),
            ({"seconds": 45}, True),
            ({"hours": 2, "minutes": 30}, True),
            ({}, False),  # No parameters should fail
        ],
    )
    async def test_add_job_interval_success(self, scheduler_adapter, interval_params, expected):
        """Test successful interval job addition with various parameters"""

        async def dummy_func():
            pass

        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=None), patch.object(
            scheduler_adapter.scheduler, "remove_job"
        ), patch.object(scheduler_adapter.scheduler, "add_job") as mock_add_job:

            result = await scheduler_adapter.add_job(
                job_id="test_job", func=dummy_func, trigger="interval", **interval_params
            )

            assert result is expected
            if expected:
                mock_add_job.assert_called_once()
            else:
                mock_add_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_job_interval_no_params(self, scheduler_adapter):
        """Test interval job without valid parameters"""

        async def dummy_func():
            pass

        result = await scheduler_adapter.add_job(job_id="test_job", func=dummy_func, trigger="interval")

        assert result is False

    @pytest.mark.asyncio
    async def test_add_job_unsupported_trigger(self, scheduler_adapter):
        """Test job with unsupported trigger"""

        async def dummy_func():
            pass

        result = await scheduler_adapter.add_job(job_id="test_job", func=dummy_func, trigger="unsupported")

        assert result is False

    @pytest.mark.asyncio
    async def test_add_job_existing_removed(self, scheduler_adapter):
        """Test that existing job is removed before adding new one"""

        async def dummy_func():
            pass

        mock_existing_job = Mock()
        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=mock_existing_job), patch.object(
            scheduler_adapter.scheduler, "remove_job"
        ) as mock_remove, patch.object(scheduler_adapter.scheduler, "add_job"):

            result = await scheduler_adapter.add_job(
                job_id="test_job", func=dummy_func, trigger="cron", cron_expr="0 0 * * *"
            )

            assert result is True
            mock_remove.assert_called_once_with("test_job")

    @pytest.mark.asyncio
    async def test_remove_job_success(self, scheduler_adapter):
        """Test successful job removal"""
        mock_job = Mock()
        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=mock_job), patch.object(
            scheduler_adapter.scheduler, "remove_job"
        ) as mock_remove:

            result = await scheduler_adapter.remove_job("test_job")

            assert result is True
            mock_remove.assert_called_once_with("test_job")

    @pytest.mark.asyncio
    async def test_remove_job_not_found(self, scheduler_adapter):
        """Test job removal when job not found"""
        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=None):
            result = await scheduler_adapter.remove_job("test_job")

            assert result is False

    @pytest.mark.asyncio
    async def test_remove_job_exception(self, scheduler_adapter):
        """Test job removal with exception"""
        with patch.object(scheduler_adapter.scheduler, "get_job", side_effect=Exception("Remove error")):
            result = await scheduler_adapter.remove_job("test_job")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_jobs_success(self, scheduler_adapter):
        """Test successful get jobs"""
        mock_job = Mock()
        mock_job.id = "job1"
        mock_job.name = "Job 1"
        mock_job.next_run_time = datetime(2024, 1, 1, 0, 0, 0)
        mock_job.trigger = Mock()
        mock_job.trigger.__str__ = Mock(return_value="cron[0 0 * * *]")
        mock_job.func.__name__ = "dummy_func"

        with patch.object(scheduler_adapter.scheduler, "get_jobs", return_value=[mock_job]):
            result = await scheduler_adapter.get_jobs()

            assert len(result) == 1
            assert result[0]["id"] == "job1"
            assert result[0]["name"] == "Job 1"
            assert result[0]["next_run_time"] == "2024-01-01T00:00:00"
            assert result[0]["trigger"] == "cron[0 0 * * *]"
            assert result[0]["func"] == "dummy_func"

    @pytest.mark.asyncio
    async def test_get_jobs_exception(self, scheduler_adapter):
        """Test get jobs with exception"""
        with patch.object(scheduler_adapter.scheduler, "get_jobs", side_effect=Exception("Get jobs error")):
            result = await scheduler_adapter.get_jobs()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_job_success(self, scheduler_adapter):
        """Test successful get job"""
        mock_job = Mock()
        mock_job.id = "job1"
        mock_job.name = "Job 1"
        mock_job.next_run_time = datetime(2024, 1, 1, 0, 0, 0)
        mock_job.trigger = Mock()
        mock_job.trigger.__str__ = Mock(return_value="cron[0 0 * * *]")
        mock_job.func.__name__ = "dummy_func"

        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=mock_job):
            result = await scheduler_adapter.get_job("job1")

            assert result is not None
            assert result["id"] == "job1"
            assert result["name"] == "Job 1"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, scheduler_adapter):
        """Test get job when not found"""
        with patch.object(scheduler_adapter.scheduler, "get_job", return_value=None):
            result = await scheduler_adapter.get_job("job1")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_job_exception(self, scheduler_adapter):
        """Test get job with exception"""
        with patch.object(scheduler_adapter.scheduler, "get_job", side_effect=Exception("Get job error")):
            result = await scheduler_adapter.get_job("job1")

            assert result is None

    def test_is_running_not_started(self, scheduler_adapter):
        """Test is_running when not started"""
        assert scheduler_adapter.is_running() is False

    def test_is_running_started(self, scheduler_adapter):
        """Test is_running when started"""
        scheduler_adapter._running = True
        mock_scheduler = Mock()
        mock_scheduler.running = True
        scheduler_adapter.scheduler = mock_scheduler
        assert scheduler_adapter.is_running() is True

    def test_validate_trigger_cron_valid(self, scheduler_adapter):
        """Test cron trigger validation with valid expression"""
        result = scheduler_adapter._validate_trigger("cron", cron_expr="0 0 * * *")
        assert result is True

    def test_validate_trigger_cron_invalid(self, scheduler_adapter):
        """Test cron trigger validation with invalid expression"""
        result = scheduler_adapter._validate_trigger("cron", cron_expr="invalid")
        assert result is False

    def test_validate_trigger_cron_no_expression(self, scheduler_adapter):
        """Test cron trigger validation without expression"""
        result = scheduler_adapter._validate_trigger("cron")
        assert result is False

    def test_validate_trigger_date_valid(self, scheduler_adapter):
        """Test date trigger validation with run_date"""
        result = scheduler_adapter._validate_trigger("date", run_date="2024-01-01T00:00:00")
        assert result is True

    def test_validate_trigger_date_no_run_date(self, scheduler_adapter):
        """Test date trigger validation without run_date"""
        result = scheduler_adapter._validate_trigger("date")
        assert result is False

    def test_validate_trigger_interval_valid(self, scheduler_adapter):
        """Test interval trigger validation with valid params"""
        result = scheduler_adapter._validate_trigger("interval", hours=1)
        assert result is True

    def test_validate_trigger_interval_invalid(self, scheduler_adapter):
        """Test interval trigger validation without valid params"""
        result = scheduler_adapter._validate_trigger("interval")
        assert result is False

    def test_validate_trigger_unsupported(self, scheduler_adapter):
        """Test validation of unsupported trigger"""
        result = scheduler_adapter._validate_trigger("unsupported")
        assert result is False
