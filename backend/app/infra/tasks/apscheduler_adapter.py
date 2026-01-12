#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APScheduler adapter implementing IScheduler interface
"""

from typing import List, Dict, Any, Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .interfaces import IScheduler
from core.logging import get_logger

logger = get_logger(__name__)


class APSchedulerAdapter(IScheduler):
    """APScheduler implementation of IScheduler interface"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._running = False

    async def start(self) -> bool:
        """Start the APScheduler"""
        try:
            if not self._running:
                self.scheduler.start()
                self._running = True
                logger.info("APScheduler started successfully")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to start APScheduler: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the APScheduler"""
        try:
            if self._running:
                self.scheduler.shutdown(wait=True)
                self._running = False
                logger.info("APScheduler stopped successfully")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to stop APScheduler: {e}")
            return False

    async def add_job(self, job_id: str, func: Callable, trigger: str, **trigger_args) -> bool:
        """Add a scheduled job"""
        try:
            # Validate trigger parameters first
            if not self._validate_trigger(trigger, **trigger_args):
                return False

            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Create trigger based on type
            if trigger == "cron":
                cron_expr = trigger_args.get("cron_expr", "")
                # Parse cron expression (minute hour day month day_of_week)
                parts = cron_expr.split()
                if len(parts) >= 5:
                    minute, hour, day, month, day_of_week = parts[:5]
                    trigger_obj = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)
                else:
                    logger.error(f"Invalid cron expression for job {job_id}: {cron_expr}")
                    return False

            elif trigger == "date":
                run_date = trigger_args.get("run_date")
                if not run_date:
                    logger.error(f"No run_date provided for job {job_id}")
                    return False
                trigger_obj = DateTrigger(run_date=run_date)

            elif trigger == "interval":
                weeks = trigger_args.get("weeks", 0)
                days = trigger_args.get("days", 0)
                hours = trigger_args.get("hours", 0)
                minutes = trigger_args.get("minutes", 0)
                seconds = trigger_args.get("seconds", 0)
                trigger_obj = IntervalTrigger(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
            else:
                logger.error(f"Unsupported trigger type for job {job_id}: {trigger}")
                return False

            # Add job to scheduler
            self.scheduler.add_job(func, trigger=trigger_obj, id=job_id, name=job_id, max_instances=1, coalesce=True)

            logger.info(f"Job {job_id} added successfully with trigger {trigger}")
            return True

        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}")
            return False

    async def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Job {job_id} removed successfully")
                return True
            else:
                logger.warning(f"Job {job_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False

    async def get_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger),
                        "func": job.func.__name__ if hasattr(job.func, "__name__") else str(job.func),
                    }
                )
            return jobs
        except Exception as e:
            logger.error(f"Failed to get jobs: {e}")
            return []

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "func": job.func.__name__ if hasattr(job.func, "__name__") else str(job.func),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running and self.scheduler.running

    def _validate_trigger(self, trigger: str, **trigger_args) -> bool:
        """Validate trigger parameters"""
        try:
            if trigger == "cron":
                cron_expr = trigger_args.get("cron_expr", "")
                if not cron_expr:
                    logger.error("No cron expression provided")
                    return False

                # Validate cron expression format
                parts = cron_expr.split()
                if len(parts) < 5:
                    logger.error(f"Invalid cron expression format: {cron_expr}")
                    return False

                # Try to create CronTrigger to validate
                try:
                    minute, hour, day, month, day_of_week = parts[:5]
                    CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)
                except Exception as e:
                    logger.error(f"Invalid cron expression: {cron_expr} - {e}")
                    return False

            elif trigger == "date":
                run_date = trigger_args.get("run_date")
                if not run_date:
                    logger.error("No run_date provided for date trigger")
                    return False

            elif trigger == "interval":
                # Basic validation for interval parameters
                valid_params = ["weeks", "days", "hours", "minutes", "seconds"]
                has_valid_param = any(trigger_args.get(param, 0) > 0 for param in valid_params)
                if not has_valid_param:
                    logger.error("No valid interval parameters provided")
                    return False

            else:
                logger.error(f"Unsupported trigger type: {trigger}")
                return False

            return True

        except Exception as e:
            logger.error(f"Trigger validation error: {e}")
            return False
