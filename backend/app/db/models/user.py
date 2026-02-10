#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User model for authentication and authorization
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from db.models.base import BaseModel


class UserRole:
    """User roles enum"""

    ADMIN = "admin"
    OPERATOR = "operator"

    @classmethod
    def all(cls):
        return [cls.ADMIN, cls.OPERATOR]

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.all()


class User(BaseModel):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.OPERATOR, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN

    def is_operator(self) -> bool:
        """Check if user has operator role"""
        return self.role == UserRole.OPERATOR

    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until is None:
            return False
        from datetime import datetime, timezone

        return self.locked_until > datetime.now(timezone.utc)

    def can_login(self) -> bool:
        """Check if user can login"""
        return self.is_active and not self.is_locked()

    def increment_failed_attempts(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1

    def reset_failed_attempts(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0

    def lock_account(self, lock_duration_minutes: int = 30):
        """Lock account for specified duration"""
        from datetime import datetime, timezone, timedelta

        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)

    def unlock_account(self):
        """Unlock account"""
        self.locked_until = None
        self.failed_login_attempts = 0
