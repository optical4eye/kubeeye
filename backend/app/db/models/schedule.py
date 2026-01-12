#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database model for scheduled tasks
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, Index
from db.models.base import BaseModel


class ScheduledTask(BaseModel):
    """Database model for scheduled tasks"""

    __tablename__ = "scheduled_tasks"

    # Core identification
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Target
    cluster_name = Column(String(255), nullable=False, index=True)

    # Scheduling
    task_type = Column(String(50), default="cron")  # cron, once, hourly, daily, weekly, monthly
    cron_expr = Column(String(255), nullable=True)
    run_datetime = Column(DateTime(timezone=True), nullable=True)  # For one-time tasks

    # Configuration
    rules = Column(JSON, nullable=True)  # Inspection rules configuration
    enabled = Column(Boolean, default=True, nullable=False)

    # Execution tracking
    last_run = Column(DateTime(timezone=True), nullable=True, index=True)
    last_status = Column(String(50), nullable=True)  # success, failed, running
    next_run = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_scheduled_tasks_cluster", "cluster_name"),
        Index("idx_scheduled_tasks_enabled", "enabled"),
        Index("idx_scheduled_tasks_next_run", "next_run"),
        Index("idx_scheduled_tasks_type", "task_type"),
        Index("idx_scheduled_tasks_last_run", "last_run"),
        Index("idx_scheduled_tasks_last_status", "last_status"),
        # Composite indexes for complex queries
        Index("idx_scheduled_tasks_pending_one_time", "task_type", "enabled", "run_datetime", "last_run"),
        Index("idx_scheduled_tasks_cluster_enabled", "cluster_name", "enabled"),
        Index("idx_scheduled_tasks_enabled_next_run", "enabled", "next_run"),  # For finding next tasks to run
        Index("idx_scheduled_tasks_cluster_type", "cluster_name", "task_type"),  # For filtering by cluster and type
        Index("idx_scheduled_tasks_created_at", "created_at"),  # For ordering by creation time
    )

    def __repr__(self):
        return f"<ScheduledTask(task_id='{self.task_id}', name='{self.name}', cluster='{self.cluster_name}', enabled={self.enabled})>"
