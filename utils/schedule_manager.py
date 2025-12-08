#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schedule manager — for managing scheduled inspection tasks
"""

import json
import os
import time
from datetime import datetime as dt
from pathlib import Path
import threading
import schedule
from croniter import croniter
import logging

# Import inspection modules
from utils.cluster_config import get_cluster
from utils.inspection_result import InspectionResult
from inspectors.node.node_inspector import NodeInspector
from inspectors.prometheus.prometheus_inspector import PrometheusInspector
from inspectors.opa.opa_inspector import OpaInspector

# Log setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ScheduleManager")

# Directory for storing schedule tasks
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCHEDULE_DIR = DATA_DIR / "schedules"
SCHEDULE_FILE = SCHEDULE_DIR / "schedules.json"

# Ensure directory exists
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

# Global objects for thread and stop event
_scheduler_thread = None
_stop_event = threading.Event()

class ScheduleTask:
    """Schedule task class"""
    def __init__(self, task_id=None, cluster=None, name=None, description=None,
                 cron_expr=None, enabled=True, rules=None, task_type="cron",
                 last_run=None, last_status=None, created_at=None, run_datetime=None):
        self.task_id = task_id or f"task_{int(time.time())}"
        self.cluster = cluster
        self.name = name or f"Inspection task {self.task_id}"
        self.description = description or ""
        self.cron_expr = cron_expr
        self.enabled = enabled
        self.rules = rules or {}
        self.task_type = task_type  # cron, monthly, weekly, daily, hourly, once
        self.last_run = last_run
        self.last_status = last_status
        self.created_at = created_at or dt.now().isoformat()
        self.run_datetime = run_datetime  # For one-time tasks

    def to_dict(self):
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "cluster": self.cluster,
            "name": self.name,
            "description": self.description,
            "cron_expr": self.cron_expr,
            "enabled": self.enabled,
            "rules": self.rules,
            "task_type": self.task_type,
            "last_run": self.last_run,
            "last_status": self.last_status,
            "created_at": self.created_at,
            "run_datetime": self.run_datetime
        }

    @classmethod
    def from_dict(cls, data):
        """Create task from dictionary"""
        return cls(
            task_id=data.get("task_id"),
            cluster=data.get("cluster"),
            name=data.get("name"),
            description=data.get("description"),
            cron_expr=data.get("cron_expr"),
            enabled=data.get("enabled", True),
            rules=data.get("rules", {}),
            task_type=data.get("task_type", "cron"),
            last_run=data.get("last_run"),
            last_status=data.get("last_status"),
            created_at=data.get("created_at"),
            run_datetime=data.get("run_datetime")
        )

    def is_valid_cron(self):
        """Check cron expression validity"""
        try:
            if self.cron_expr:
                croniter(self.cron_expr)
                return True
        except Exception:
            return False
        return False

    def get_next_run(self):
        """Get next run time"""
        if self.cron_expr and self.is_valid_cron():
            base = dt.now()
            itr = croniter(self.cron_expr, base)
            return itr.get_next(dt)
        return None

    def get_pretty_schedule(self):
        """Get human-readable schedule description"""
        if self.task_type == "cron":
            return f"Custom: {self.cron_expr}"
        elif self.task_type == "once":
            return f"One-time: {self.run_datetime}"
        elif self.task_type == "hourly":
            return "Every hour"
        elif self.task_type == "daily":
            return "Every day"
        elif self.task_type == "weekly":
            return "Every week"
        elif self.task_type == "monthly":
            return "Every month"
        return "Unknown schedule type"

def load_schedules():
    """Load all schedule tasks"""
    if not SCHEDULE_FILE.exists():
        save_schedules([])
        return []

    try:
        with open(SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
            return [ScheduleTask.from_dict(task) for task in data]
    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        return []

def save_schedules(tasks):
    """Save all schedule tasks"""
    try:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump([task.to_dict() for task in tasks], f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving schedule: {e}")
        return False

def add_schedule(task):
    """Add or update schedule task"""
    tasks = load_schedules()
    for i, t in enumerate(tasks):
        if t.task_id == task.task_id:
            tasks[i] = task
            return save_schedules(tasks)
    tasks.append(task)
    return save_schedules(tasks)

def delete_schedule(task_id):
    """Delete schedule task by ID"""
    tasks = load_schedules()
    tasks = [t for t in tasks if t.task_id != task_id]
    return save_schedules(tasks)

def get_schedule(task_id):
    """Get task by ID"""
    tasks = load_schedules()
    for task in tasks:
        if task.task_id == task_id:
            return task
    return None

def update_task_status(task_id, last_run=None, last_status=None):
    """Update task status"""
    task = get_schedule(task_id)
    if task:
        task.last_run = last_run or dt.now().isoformat()
        task.last_status = last_status
        return add_schedule(task)
    return False

def run_inspection_bg(task):
    """Execute inspection in background"""
    try:
        logger.info(f"Starting inspection task: {task.name} ({task.task_id})")
        update_task_status(task.task_id, last_status="running")
        from components.ui.task_execution import execute_inspection_task
        success, message, _ = execute_inspection_task(task, show_progress=False)
        if success:
            update_task_status(task.task_id, last_status="success")
            logger.info(f"Task completed: {task.name} ({task.task_id})")
        else:
            update_task_status(task.task_id, last_status="failed")
            logger.error(f"Task execution error: {task.name} ({task.task_id}) - {message}")
        return success
    except Exception as e:
        logger.error(f"Task execution error: {e}", exc_info=True)
        update_task_status(task.task_id, last_status="failed")
        return False

def run_inspection(task_id, return_results=False):
    """Start inspection by task ID
    If return_results=True, return results instead of running in background
    """
    task = get_schedule(task_id)
    if not task:
        logger.error(f"Task not found: {task_id}")
        return (False, "Task not found", None) if return_results else (False, "Task not found")
    try:
        if return_results:
            from components.ui.task_execution import execute_inspection_task
            success, message, results = execute_inspection_task(task, show_progress=True)
            return success, message, results
        else:
            threading.Thread(target=lambda: run_inspection_bg(task)).start()
            return True, "Task started"
    except Exception as e:
        logger.error(f"Task start error: {e}")
        return (False, str(e), None) if return_results else (False, str(e))

def _scheduler_loop():
    """Scheduler run loop, runs in separate thread"""
    while not _stop_event.is_set():
        schedule.run_pending()
        tasks = load_schedules()
        now = dt.now()
        for task in tasks:
            if (task.enabled and task.task_type == "once" and task.run_datetime and not task.last_run):
                try:
                    run_dt = dt.strptime(task.run_datetime, "%Y-%m-%d %H:%M")
                except Exception:
                    continue
                if now >= run_dt:
                    logger.info(f"Executing one-time task: {task.name} ({task.task_id})")
                    success = run_inspection_bg(task)
                    task.enabled = False
                    add_schedule(task)
                    schedule.clear(task.task_id)
        time.sleep(30)

def schedule_tasks():
    """Configure all enabled schedule tasks"""
    schedule.clear()
    tasks = load_schedules()
    for task in tasks:
        if not task.enabled:
            continue
        if task.task_type == "cron" and task.is_valid_cron():
            def create_cron_job(task_obj):
                def cron_job():
                    run_inspection_bg(task_obj)
                    reschedule_cron_task(task_obj)
                return cron_job
            from croniter import croniter
            base = dt.now()
            cron = croniter(task.cron_expr, base)
            next_run = cron.get_next(dt)
            delta_seconds = (next_run - base).total_seconds()
            if delta_seconds < 60:
                next_run = cron.get_next(dt)
                delta_seconds = (next_run - base).total_seconds()
            schedule.every(int(delta_seconds)).seconds.do(create_cron_job(task)).tag(task.task_id)
            logger.info(f"Scheduled Cron task: {task.name} ({task.task_id}) at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        elif task.task_type == "hourly":
            schedule.every().hour.do(lambda t=task: run_inspection_bg(t)).tag(task.task_id)
        elif task.task_type == "daily":
            schedule.every().day.at("00:00").do(lambda t=task: run_inspection_bg(t)).tag(task.task_id)
        elif task.task_type == "weekly":
            schedule.every().monday.at("00:00").do(lambda t=task: run_inspection_bg(t)).tag(task.task_id)
        elif task.task_type == "monthly":
            schedule.every().day.at("00:00").do(lambda t=task: run_inspection_bg(t) if dt.now().day == 1 else None).tag(task.task_id)
        elif task.task_type == "once" and task.run_datetime:
            run_time = dt.fromisoformat(task.run_datetime)
            now = dt.now()
            if run_time > now:
                delta_seconds = (run_time - now).total_seconds()
                schedule.every(int(delta_seconds)).seconds.do(lambda t=task: run_inspection_bg(t)).tag(task.task_id)
                logger.info(f"Scheduled one-time task: {task.name} ({task.task_id}) at {run_time}")

    logger.info(f"Scheduled {len([t for t in tasks if t.enabled])} active tasks")

def reschedule_cron_task(task):
    """Reschedule next cron task execution"""
    try:
        schedule.clear(task.task_id)
        from croniter import croniter
        base = dt.now()
        cron = croniter(task.cron_expr, base)
        next_run = cron.get_next(dt)
        delta_seconds = (next_run - base).total_seconds()
        def create_cron_job(task_obj):
            def cron_job():
                run_inspection_bg(task_obj)
                reschedule_cron_task(task_obj)
            return cron_job
        schedule.every(int(delta_seconds)).seconds.do(create_cron_job(task)).tag(task.task_id)
        logger.info(f"Rescheduled Cron task: {task.name} ({task.task_id}) at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"Error rescheduling task {task.name} ({task.task_id}): {e}")

def start_scheduler():
    """Start scheduler"""
    global _scheduler_thread, _stop_event
    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.info("Scheduler already running")
        return
    schedule_tasks()
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop)
    _scheduler_thread.daemon = True
    _scheduler_thread.start()
    logger.info("Scheduler started")
    return True

def stop_scheduler():
    """Stop scheduler"""
    global _scheduler_thread, _stop_event
    if not _scheduler_thread or not _scheduler_thread.is_alive():
        logger.info("Scheduler not running")
        return
    _stop_event.set()
    _scheduler_thread.join(timeout=5)
    _scheduler_thread = None
    logger.info("Scheduler stopped")
    return True

def restart_scheduler():
    """Restart scheduler"""
    stop_scheduler()
    return start_scheduler()

try:
    start_scheduler()
except Exception as e:
    logger.error(f"Error starting scheduler: {e}")
