#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit log model for tracking user actions
"""

from sqlalchemy import Column, String, Text, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from db.models.base import BaseModel
import uuid


class AuditAction:
    """Audit action types - simple action names, resource type stored separately"""

    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    RUN = "run"
    CHECK = "check"
    SCAN = "scan"

    @classmethod
    def all(cls):
        return [
            cls.LOGIN,
            cls.LOGOUT,
            cls.CREATE,
            cls.UPDATE,
            cls.DELETE,
            cls.READ,
            cls.RUN,
            cls.CHECK,
            cls.SCAN,
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True)
    resource_name = Column(String(255), nullable=True)  # Human-readable resource name
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
            "resource_name": self.resource_name,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
