#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service for automatic cleanup of old inspection reports from database
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from db.database import get_db
from db.database_context import with_db_session
from db.models.inspection_result import InspectionResult
from core.logging import get_logger

logger = get_logger(__name__)


class ReportCleanupService:
    """Service for cleaning up old inspection reports from database"""

    def __init__(self):
        logger.info("Initializing ReportCleanupService")
        self.retention_days = self._get_retention_days()
        logger.info(f"ReportCleanupService initialized with retention_days={self.retention_days}")

    def _get_retention_days(self) -> int:
        """Get retention days from settings"""
        try:
            retention_days = int(settings.kubeeye_report_retention_days)
            result = max(0, retention_days)  # Ensure non-negative
        except (ValueError, TypeError):
            logger.warning(f"Invalid retention days value: {settings.kubeeye_report_retention_days}, using default 0")
            result = 0
        logger.info(f"ReportCleanupService retention_days set to {result}")
        return result

    async def cleanup_old_reports(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Clean up old inspection reports from database

        Args:
            retention_days: number of days to keep reports (overrides config)

        Returns:
            Dict with cleanup results
        """
        logger.info(f"Starting cleanup_old_reports with retention_days={retention_days}")
        if retention_days is None:
            retention_days = self.retention_days

        if retention_days < 0:
            logger.warning("Negative retention days provided, skipping cleanup")
            return {"deleted_count": 0, "error": "Invalid retention days"}

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        logger.info(f"Starting cleanup of inspection reports older than {cutoff_date}")

        deleted_count = 0
        error = None

        try:
            async with with_db_session() as db:
                logger.info("Counting records to be deleted")
                # Count records to be deleted
                count_stmt = select(func.count(InspectionResult.id)).where(InspectionResult.timestamp < cutoff_date)
                count_result = await db.execute(count_stmt)
                records_to_delete = count_result.scalar()
                logger.info(f"Found {records_to_delete} records to delete")

                if records_to_delete == 0:
                    logger.info("No old reports found for cleanup")
                    return {
                        "deleted_count": 0,
                        "cutoff_date": cutoff_date.isoformat(),
                        "retention_days": retention_days,
                        "message": "No old reports found for cleanup",
                    }

                logger.info("Deleting old records")
                # Delete old records
                delete_stmt = delete(InspectionResult).where(InspectionResult.timestamp < cutoff_date)
                result = await db.execute(delete_stmt)
                await db.commit()

                deleted_count = result.rowcount

                logger.info(f"Successfully deleted {deleted_count} old inspection reports")

                return {
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "retention_days": retention_days,
                    "message": f"Successfully deleted {deleted_count} old reports",
                }

        except Exception as e:
            error_msg = f"Failed to cleanup old reports: {str(e)}"
            logger.error(error_msg)
            return {
                "deleted_count": 0,
                "error": error_msg,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": retention_days,
            }

    async def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about reports that would be cleaned up

        Returns:
            Dict with cleanup statistics
        """
        logger.info("Starting get_cleanup_stats")
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        try:
            async with with_db_session() as db:
                logger.info("Counting total records")
                # Count total records
                total_stmt = select(func.count(InspectionResult.id))
                total_result = await db.execute(total_stmt)
                total_records = total_result.scalar()
                logger.info(f"Total records: {total_records}")

                logger.info("Counting old records")
                # Count old records
                old_stmt = select(func.count(InspectionResult.id)).where(InspectionResult.timestamp < cutoff_date)
                old_result = await db.execute(old_stmt)
                old_records = old_result.scalar()
                logger.info(f"Old records: {old_records}")

                # Count recent records
                recent_records = total_records - old_records

                logger.info(f"Cleanup stats: total={total_records}, old={old_records}, recent={recent_records}")
                return {
                    "total_records": total_records,
                    "old_records": old_records,
                    "recent_records": recent_records,
                    "cutoff_date": cutoff_date.isoformat(),
                    "retention_days": self.retention_days,
                    "cleanup_percentage": round((old_records / total_records * 100) if total_records > 0 else 0, 2),
                }

        except Exception as e:
            error_msg = f"Failed to get cleanup stats: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "retention_days": self.retention_days, "cutoff_date": cutoff_date.isoformat()}

    async def delete_reports_by_cluster(
        self, cluster_name: str, retention_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Clean up old inspection reports for specific cluster

        Args:
            cluster_name: name of the cluster
            retention_days: number of days to keep reports (overrides config)

        Returns:
            Dict with cleanup results
        """
        if retention_days is None:
            retention_days = self.retention_days

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        logger.info(f"Starting cleanup of reports for cluster '{cluster_name}' older than {cutoff_date}")

        try:
            async with with_db_session() as db:
                # Count records to be deleted
                count_stmt = select(func.count(InspectionResult.id)).where(
                    InspectionResult.cluster_name == cluster_name, InspectionResult.timestamp < cutoff_date
                )
                count_result = await db.execute(count_stmt)
                records_to_delete = count_result.scalar()

                if records_to_delete == 0:
                    logger.info(f"No old reports found for cluster '{cluster_name}'")
                    return {
                        "deleted_count": 0,
                        "cluster_name": cluster_name,
                        "cutoff_date": cutoff_date.isoformat(),
                        "retention_days": retention_days,
                        "message": f"No old reports found for cluster '{cluster_name}'",
                    }

                # Delete old records
                delete_stmt = delete(InspectionResult).where(
                    InspectionResult.cluster_name == cluster_name, InspectionResult.timestamp < cutoff_date
                )
                result = await db.execute(delete_stmt)
                await db.commit()

                deleted_count = result.rowcount

                logger.info(f"Successfully deleted {deleted_count} old reports for cluster '{cluster_name}'")

                return {
                    "deleted_count": deleted_count,
                    "cluster_name": cluster_name,
                    "cutoff_date": cutoff_date.isoformat(),
                    "retention_days": retention_days,
                    "message": f"Successfully deleted {deleted_count} old reports for cluster '{cluster_name}'",
                }

        except Exception as e:
            error_msg = f"Failed to cleanup reports for cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            return {
                "deleted_count": 0,
                "cluster_name": cluster_name,
                "error": error_msg,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": retention_days,
            }


# Global service instance
_cleanup_service = None


def get_report_cleanup_service() -> ReportCleanupService:
    """Get report cleanup service instance"""
    global _cleanup_service
    if _cleanup_service is None:
        logger.info("Creating new ReportCleanupService instance")
        _cleanup_service = ReportCleanupService()
    return _cleanup_service


async def cleanup_old_reports(retention_days: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience function for cleaning up old reports

    Args:
        retention_days: number of days to keep reports (overrides config)

    Returns:
        Dict with cleanup results
    """
    service = get_report_cleanup_service()
    return await service.cleanup_old_reports(retention_days)


async def get_cleanup_stats() -> Dict[str, Any]:
    """
    Convenience function for getting cleanup statistics

    Returns:
        Dict with cleanup statistics
    """
    service = get_report_cleanup_service()
    return await service.get_cleanup_stats()


async def cleanup_reports_by_cluster(cluster_name: str, retention_days: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience function for cleaning up reports by cluster

    Args:
        cluster_name: name of the cluster
        retention_days: number of days to keep reports (overrides config)

    Returns:
        Dict with cleanup results
    """
    service = get_report_cleanup_service()
    return await service.delete_reports_by_cluster(cluster_name, retention_days)
