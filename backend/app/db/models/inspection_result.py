#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database model for inspection results
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.sql import func
from db.models.base import BaseModel


class InspectionResult(BaseModel):
    """Database model for inspection results"""

    __tablename__ = "inspection_results"

    # Core identification fields
    result_id = Column(String(255), unique=True, nullable=False, index=True)
    cluster_name = Column(String(255), nullable=False, index=True)
    inspection_type = Column(String(100), nullable=False, index=True)

    # Timestamp (separate from base model for explicit control)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Statistics fields (for efficient querying)
    total_items = Column(Integer, default=0, nullable=False)
    passed_count = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)

    # Full result data stored as JSON
    result_data = Column(JSON, nullable=False)

    # Metadata
    execution_duration = Column(Integer, nullable=True)  # in seconds
    triggered_by = Column(String(50), default="user", index=True)  # user, scheduler
    inspectors_used = Column(JSON, nullable=True)  # list of inspector names

    # Indexes for common queries
    __table_args__ = (
        Index("idx_inspection_results_cluster_timestamp", "cluster_name", "timestamp"),
        Index("idx_inspection_results_type_timestamp", "inspection_type", "timestamp"),
        Index("idx_inspection_results_cluster_type", "cluster_name", "inspection_type"),
        Index("idx_inspection_results_timestamp_desc", "timestamp"),  # For latest results queries
        Index("idx_inspection_results_result_id", "result_id"),  # For lookups by result_id
        Index("idx_inspection_results_triggered_by", "triggered_by"),  # For filtering by trigger type
        Index("idx_inspection_results_critical_count", "critical_count"),  # For filtering by severity
        Index(
            "idx_inspection_results_cluster_type_timestamp", "cluster_name", "inspection_type", "timestamp"
        ),  # Complex queries
    )

    def __repr__(self):
        return f"<InspectionResult(result_id='{self.result_id}', cluster='{self.cluster_name}', type='{self.inspection_type}')>"
