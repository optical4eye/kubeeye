#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit log model for tracking user actions
"""

from sqlalchemy import Column, String, DateTime, Text, Index, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from db.models.base import BaseModel
import uuid


class AuditAction:
    """Audit action types"""
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    CLUSTER_CREATE = "cluster_create"
    CLUSTER_UPDATE = "cluster_update"
    CLUSTER_DELETE = "cluster_delete"
    INSPECTION_RUN = "inspection_run"
    INSPECTION_DELETE = "inspection_delete"
    REPORT_VIEW = "report_view"
    REPORT_EXPORT = "report_export"
    REPORT_DELETE = "report_delete"
    SECRET_CREATE = "secret_create"
    SECRET_UPDATE = "secret_update"
    SECRET_DELETE = "secret_delete"
    RULE_UPDATE = "rule_update"
    GITOPS_SYNC = "gitops_sync"
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_RUN = "task_run"
    NETWORK_CHECK = "network_check"
    POPEYE_SCAN = "popeye_scan"
    CLEANUP_RUN = "cleanup_run"
    QUEUE_CLEAR = "queue_clear"

    @classmethod
    def all(cls):
        return [
            cls.LOGIN, cls.LOGOUT, cls.PASSWORD_CHANGE,
            cls.USER_CREATE, cls.USER_UPDATE, cls.USER_DELETE,
            cls.CLUSTER_CREATE, cls.CLUSTER_UPDATE, cls.CLUSTER_DELETE,
            cls.INSPECTION_RUN, cls.INSPECTION_DELETE,
            cls.REPORT_VIEW, cls.REPORT_EXPORT, cls.REPORT_DELETE,
            cls.SECRET_CREATE, cls.SECRET_UPDATE, cls.SECRET_DELETE,
            cls.RULE_UPDATE, cls.GITOPS_SYNC,
            cls.TASK_CREATE, cls.TASK_UPDATE, cls.TASK_DELETE, cls.TASK_RUN,
            cls.NETWORK_CHECK, cls.POPEYE_SCAN,
            cls.CLEANUP_RUN, cls.QUEUE_CLEAR
        ]


class AuditStatus:
    """Audit status types"""
    SUCCESS = "success"
    FAILURE = "failure"

    @classmethod
    def all(cls):
        return [cls.SUCCESS, cls.FAILURE]


class AuditLog(BaseModel):
    """Audit log model for tracking user actions"""

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default=AuditStatus.SUCCESS, index=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', status='{self.status}')>"

    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
