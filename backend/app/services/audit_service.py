#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit service for tracking user actions
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.audit_log_repository import AuditLogRepository
from db.models.audit_log import AuditLog, AuditAction, AuditStatus
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for audit logging"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_log_repo = AuditLogRepository(session)

    async def log_action(
        self,
        user_id: int,
        username: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = AuditStatus.SUCCESS,
        error_message: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """
        Log user action

        Args:
            user_id: User ID
            username: Username
            action: Action type
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details
            ip_address: Client IP address
            user_agent: Client user agent
            status: Status of action (success/failure)
            error_message: Error message if action failed

        Returns:
            Created audit log
        """
        try:
            # Check if audit is enabled
            if not settings.kubeeye_audit_enabled:
                logger.debug("Audit logging is disabled")
                return None

            audit_log = await self.audit_log_repo.create(
                {
                    "user_id": user_id,
                    "username": username,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": details,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "status": status,
                    "error_message": error_message,
                }
            )

            logger.debug(
                f"Audit log created: user={username}, action={action}, "
                f"resource={resource_type}:{resource_id}, status={status}"
            )

            return audit_log
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            # Don't raise exception to avoid breaking main flow
            return None

    async def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get audit logs with filtering and pagination

        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            user_id: Filter by user ID
            username: Filter by username
            action: Filter by action type
            resource_type: Filter by resource type
            status: Filter by status
            date_from: Filter by date from
            date_to: Filter by date to

        Returns:
            Tuple of (audit logs list, total count)
        """
        try:
            audit_logs, total = await self.audit_log_repo.get_audit_logs(
                limit=limit,
                offset=offset,
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                status=status,
                date_from=date_from,
                date_to=date_to,
            )

            return [log.to_dict() for log in audit_logs], total
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise

    async def get_audit_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Get audit log by ID

        Args:
            log_id: Audit log ID

        Returns:
            Audit log details or None
        """
        try:
            audit_log = await self.audit_log_repo.get_audit_log_by_id(log_id)
            return audit_log.to_dict() if audit_log else None
        except Exception as e:
            logger.error(f"Failed to get audit log by ID {log_id}: {e}")
            raise

    async def get_audit_stats(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics

        Args:
            date_from: Filter by date from
            date_to: Filter by date to

        Returns:
            Dictionary with statistics
        """
        try:
            return await self.audit_log_repo.get_audit_stats(date_from, date_to)
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            raise

    async def cleanup_old_logs(self) -> int:
        """
        Clean up old audit logs based on retention policy

        Returns:
            Number of deleted records
        """
        try:
            retention_days = settings.kubeeye_audit_retention_days
            deleted_count = await self.audit_log_repo.delete_old_logs(days=retention_days)
            logger.info(f"Cleaned up {deleted_count} old audit logs (retention: {retention_days} days)")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            raise

    async def log_login(
        self,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """
        Log login action

        Args:
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether login was successful
            error_message: Error message if login failed

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=AuditAction.LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            error_message=error_message,
        )

    async def log_logout(
        self, user_id: int, username: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log logout action

        Args:
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id, username=username, action=AuditAction.LOGOUT, ip_address=ip_address, user_agent=user_agent
        )

    async def log_password_change(
        self, user_id: int, username: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log password change action

        Args:
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=AuditAction.PASSWORD_CHANGE,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_cluster_action(
        self,
        user_id: int,
        username: str,
        action: str,
        cluster_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """
        Log cluster action

        Args:
            user_id: User ID
            username: Username
            action: Action type (create, update, delete)
            cluster_name: Cluster name
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional details

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type="cluster",
            resource_id=cluster_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_inspection_action(
        self,
        user_id: int,
        username: str,
        action: str,
        inspection_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """
        Log inspection action

        Args:
            user_id: User ID
            username: Username
            action: Action type (run, delete)
            inspection_id: Inspection ID
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional details

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type="inspection",
            resource_id=inspection_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
