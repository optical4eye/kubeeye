#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit log repository for audit log management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.base_repository import BaseRepository
from db.models.audit_log import AuditLog
from core.logging import get_logger

logger = get_logger(__name__)


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

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
    ) -> tuple[List[AuditLog], int]:
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
            # Build query
            stmt = select(AuditLog)

            # Apply filters
            conditions = []
            if user_id:
                try:
                    user_id_int = int(user_id)
                    conditions.append(AuditLog.user_id == user_id_int)
                except (ValueError, TypeError):
                    # Invalid user_id format, skip this filter
                    pass
            if username:
                conditions.append(AuditLog.username.ilike(f"%{username}%"))
            if action:
                conditions.append(AuditLog.action == action)
            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type)
            if status:
                conditions.append(AuditLog.status == status)
            if date_from:
                conditions.append(AuditLog.created_at >= date_from)
            if date_to:
                conditions.append(AuditLog.created_at <= date_to)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await self.session.execute(count_stmt)
            total = total_result.scalar()

            # Apply pagination and ordering
            stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)

            # Execute query
            result = await self.session.execute(stmt)
            audit_logs = result.scalars().all()

            return audit_logs, total
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise

    async def get_audit_log_by_id(self, log_id: str) -> Optional[AuditLog]:
        """
        Get audit log by ID

        Args:
            log_id: Audit log ID

        Returns:
            Audit log or None
        """
        try:
            stmt = select(AuditLog).where(AuditLog.id == log_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get audit log by ID {log_id}: {e}")
            raise

    async def get_user_audit_logs(self, user_id: str, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        """
        Get audit logs for specific user

        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of audit logs
        """
        try:
            stmt = (
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get audit logs for user {user_id}: {e}")
            raise

    async def get_resource_audit_logs(
        self, resource_type: str, resource_id: str, limit: int = 100, offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for specific resource

        Args:
            resource_type: Type of resource
            resource_id: ID of resource
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of audit logs
        """
        try:
            stmt = (
                select(AuditLog)
                .where(and_(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id))
                .order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get audit logs for resource {resource_type}:{resource_id}: {e}")
            raise

    async def delete_old_logs(self, days: int = 14) -> int:
        """
        Delete audit logs older than specified days

        Args:
            days: Number of days to retain logs

        Returns:
            Number of deleted records
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            async with self.transaction():
                stmt = select(AuditLog).where(AuditLog.created_at < cutoff_date)
                result = await self.session.execute(stmt)
                old_logs = result.scalars().all()

                for log in old_logs:
                    await self.session.delete(log)

                deleted_count = len(old_logs)
                logger.info(f"Deleted {deleted_count} audit logs older than {days} days")

                return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete old audit logs: {e}")
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
            # Build base query
            stmt = select(AuditLog)
            conditions = []
            if date_from:
                conditions.append(AuditLog.created_at >= date_from)
            if date_to:
                conditions.append(AuditLog.created_at <= date_to)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Total logs
            total_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await self.session.execute(total_stmt)
            total = total_result.scalar()

            # Logs by action
            action_stmt = (
                select(AuditLog.action, func.count().label("count"))
                .select_from(stmt.subquery())
                .group_by(AuditLog.action)
            )
            action_result = await self.session.execute(action_stmt)
            by_action = {row.action: row.count for row in action_result}

            # Logs by user
            user_stmt = (
                select(AuditLog.username, func.count().label("count"))
                .select_from(stmt.subquery())
                .group_by(AuditLog.username)
                .order_by(func.count().desc())
                .limit(10)
            )
            user_result = await self.session.execute(user_stmt)
            by_user = {row.username: row.count for row in user_result}

            # Logs by status
            status_stmt = (
                select(AuditLog.status, func.count().label("count"))
                .select_from(stmt.subquery())
                .group_by(AuditLog.status)
            )
            status_result = await self.session.execute(status_stmt)
            by_status = {row.status: row.count for row in status_result}

            # Logs by resource type
            resource_stmt = (
                select(AuditLog.resource_type, func.count().label("count"))
                .select_from(stmt.subquery())
                .group_by(AuditLog.resource_type)
            )
            resource_result = await self.session.execute(resource_stmt)
            by_resource = {row.resource_type: row.count for row in resource_result if row.resource_type}

            return {
                "total": total,
                "by_action": by_action,
                "by_user": by_user,
                "by_status": by_status,
                "by_resource": by_resource,
            }
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            raise
