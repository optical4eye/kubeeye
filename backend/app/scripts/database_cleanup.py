#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from core.logging import get_logger
from core.config.settings import settings

"""
Database cleanup script for old inspection reports
Can be executed on schedule via cron or called manually
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Performance optimization: use uvloop for better asyncio performance
try:
    import uvloop
except ImportError:
    uvloop = None  # uvloop not available, use default asyncio

# Add root directory to path
ROOT_DIR = Path(__file__).parent.parent  # backend/
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = get_logger(__name__)

# Environment variable for retention days
ENV_RETENTION_DAYS = "KUBEEYE_REPORT_RETENTION_DAYS"
DEFAULT_RETENTION_DAYS = 7


def get_retention_days() -> int:
    """Get retention days from environment variable or default"""
    try:
        retention_days = settings.kubeeye_report_retention_days
        return max(0, retention_days)  # Ensure non-negative
    except (ValueError, TypeError):
        logger.warning(f"Invalid retention days, using default {DEFAULT_RETENTION_DAYS} days")
        return DEFAULT_RETENTION_DAYS


async def run_database_cleanup(retention_days: Optional[int] = None) -> Dict[str, Any]:
    """Execute database cleanup of old inspection reports

    Args:
        retention_days: number of days to keep reports (overrides config)

    Returns:
        Dict with cleanup results
    """
    try:
        from services.components.report_cleanup_service import cleanup_old_reports

        logger.info("Starting database cleanup of old inspection reports...")

        # Use provided retention days or get from config
        if retention_days is None:
            retention_days = get_retention_days()

        logger.info(f"Retention period: {retention_days} days")

        # Execute cleanup
        result = await cleanup_old_reports(retention_days)

        # Log results
        if result.get("deleted_count", 0) > 0:
            logger.info(f"Deleted {result['deleted_count']} old inspection reports")
        else:
            logger.info("No old reports found for deletion")

        if "error" in result:
            logger.error(f"Cleanup error: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        return {"deleted_count": 0, "error": str(e), "retention_days": retention_days or get_retention_days()}


async def get_cleanup_statistics() -> Dict[str, Any]:
    """Get cleanup statistics

    Returns:
        Dict with cleanup statistics
    """
    try:
        from services.components.report_cleanup_service import get_cleanup_stats

        logger.info("Getting cleanup statistics...")

        stats = await get_cleanup_stats()

        # Log statistics
        if "error" not in stats:
            logger.info(f"Total records: {stats.get('total_records', 0)}")
            logger.info(f"Old records: {stats.get('old_records', 0)}")
            logger.info(f"Recent records: {stats.get('recent_records', 0)}")
            logger.info(f"Cleanup percentage: {stats.get('cleanup_percentage', 0)}%")
        else:
            logger.error(f"Failed to get statistics: {stats['error']}")

        return stats

    except Exception as e:
        logger.error(f"Failed to get cleanup statistics: {e}")
        return {"error": str(e), "retention_days": get_retention_days()}


async def cleanup_cluster_reports(cluster_name: str, retention_days: Optional[int] = None) -> Dict[str, Any]:
    """Cleanup reports for specific cluster

    Args:
        cluster_name: name of the cluster
        retention_days: number of days to keep reports (overrides config)

    Returns:
        Dict with cleanup results
    """
    try:
        from services.components.report_cleanup_service import cleanup_reports_by_cluster

        logger.info(f"Starting cleanup for cluster '{cluster_name}'...")

        # Use provided retention days or get from config
        if retention_days is None:
            retention_days = get_retention_days()

        logger.info(f"Retention period: {retention_days} days")

        # Execute cleanup
        result = await cleanup_reports_by_cluster(cluster_name, retention_days)

        # Log results
        if result.get("deleted_count", 0) > 0:
            logger.info(f"Deleted {result['deleted_count']} old reports for cluster '{cluster_name}'")
        else:
            logger.info(f"No old reports found for cluster '{cluster_name}'")

        if "error" in result:
            logger.error(f"Cluster cleanup error: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Cluster cleanup failed: {e}")
        return {
            "deleted_count": 0,
            "cluster_name": cluster_name,
            "error": str(e),
            "retention_days": retention_days or get_retention_days(),
        }


def main():
    """Main function for running from command line"""
    import argparse

    parser = argparse.ArgumentParser(description="KubeEye database cleanup tool")
    parser.add_argument(
        "--retention-days", type=int, help=f"Number of days to keep reports (overrides {ENV_RETENTION_DAYS})"
    )
    parser.add_argument("--cluster", type=str, help="Cleanup reports for specific cluster only")
    parser.add_argument("--stats", action="store_true", help="Show cleanup statistics only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")

    args = parser.parse_args()

    async def run_command():
        if args.stats:
            # Show statistics only
            stats = await get_cleanup_statistics()
            print("\n=== Cleanup Statistics ===")
            if "error" in stats:
                print(f"Error: {stats['error']}")
            else:
                print(f"Total records: {stats.get('total_records', 0)}")
                print(f"Old records: {stats.get('old_records', 0)}")
                print(f"Recent records: {stats.get('recent_records', 0)}")
                print(f"Cleanup percentage: {stats.get('cleanup_percentage', 0)}%")
                print(f"Retention days: {stats.get('retention_days', 0)}")
                print(f"Cutoff date: {stats.get('cutoff_date', 'Unknown')}")
        elif args.cluster:
            # Cleanup specific cluster
            if args.dry_run:
                print(
                    f"DRY RUN: Would clean up reports for cluster '{args.cluster}' older than {args.retention_days or get_retention_days()} days"
                )
                return

            result = await cleanup_cluster_reports(args.cluster, args.retention_days)
            print("\n=== Cluster Cleanup Result ===")
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Cluster: {result.get('cluster_name', args.cluster)}")
                print(f"Deleted records: {result.get('deleted_count', 0)}")
                print(f"Retention days: {result.get('retention_days', 0)}")
                print(f"Cutoff date: {result.get('cutoff_date', 'Unknown')}")
                print(f"Message: {result.get('message', 'No message')}")
        else:
            # Cleanup all old reports
            if args.dry_run:
                print(f"DRY RUN: Would clean up reports older than {args.retention_days or get_retention_days()} days")
                return

            result = await run_database_cleanup(args.retention_days)
            print("\n=== Cleanup Result ===")
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Deleted records: {result.get('deleted_count', 0)}")
                print(f"Retention days: {result.get('retention_days', 0)}")
                print(f"Cutoff date: {result.get('cutoff_date', 'Unknown')}")
                print(f"Message: {result.get('message', 'No message')}")

    # Run the async command with custom loop factory if uvloop is available
    if uvloop is not None:
        asyncio.run(run_command(), loop_factory=uvloop.new_event_loop)
    else:
        asyncio.run(run_command())


if __name__ == "__main__":
    main()
