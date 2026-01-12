#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository for inspection results - Async Only
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, select, func
from db.repositories.base_repository import BaseRepository
from db.models.inspection_result import InspectionResult
from core.common.cache_utils import cached, invalidate_cache
from core.logging import get_logger

logger = get_logger(__name__)


class InspectionResultRepository(BaseRepository[InspectionResult]):
    """Async repository for inspection results operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, InspectionResult)

    @cached("inspection_results", ttl=300)
    async def get_by_result_id(self, result_id: str) -> Optional[InspectionResult]:
        """Get result by result_id"""
        return await self.get_by_field("result_id", result_id)

    async def get_by_cluster(self, cluster_name: str, limit: Optional[int] = None) -> List[InspectionResult]:
        """Get results for specific cluster"""
        return await self.get_many_by_field("cluster_name", cluster_name)

    async def get_by_type(self, inspection_type: str, limit: Optional[int] = None) -> List[InspectionResult]:
        """Get results by inspection type"""
        return await self.get_many_by_field("inspection_type", inspection_type)

    async def list_results(
        self,
        cluster_name: Optional[str] = None,
        inspection_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        exclude_inspection_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        List results with summary format and pagination metadata

        Args:
            cluster_name: Optional filter by cluster name
            inspection_type: Optional filter by inspection type
            limit: Maximum number of results to return (None for all)
            offset: Offset for pagination
            order_by: Field for sorting (e.g., "timestamp DESC")
            exclude_inspection_types: List of inspection types to exclude

        Returns:
            Dict containing:
                - results: List of inspection result summaries
                - total: Total count of results matching filters
                - limit: Limit used in query
                - offset: Offset used in query
        """
        try:
            # Build base query for counting
            count_stmt = select(func.count()).select_from(InspectionResult)

            # Build base query for results
            stmt = select(InspectionResult)

            # Apply filters to both queries
            filters = []
            if cluster_name:
                filters.append(InspectionResult.cluster_name == cluster_name)
            if inspection_type:
                filters.append(InspectionResult.inspection_type == inspection_type)
            if exclude_inspection_types:
                filters.append(InspectionResult.inspection_type.notin_(exclude_inspection_types))

            if filters:
                stmt = stmt.where(and_(*filters))
                count_stmt = count_stmt.where(and_(*filters))

            # Apply ordering
            if order_by:
                # Simple order_by parsing (e.g., "timestamp DESC")
                parts = order_by.split()
                field_name = parts[0]
                direction = parts[1] if len(parts) > 1 else "ASC"

                if hasattr(InspectionResult, field_name):
                    field = getattr(InspectionResult, field_name)
                    if direction.upper() == "DESC":
                        stmt = stmt.order_by(desc(field))
                    else:
                        stmt = stmt.order_by(field)
            else:
                # Default ordering by timestamp descending
                stmt = stmt.order_by(desc(InspectionResult.timestamp))

            # Get total count
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar()

            # Apply pagination
            if limit:
                stmt = stmt.limit(limit).offset(offset)

            # Execute query
            result = await self.session.execute(stmt)
            results = result.scalars().all()

            # Convert to summary format
            summaries = []
            for result in results:
                # Determine status
                if result.critical_count > 0:
                    status = "failed"
                elif result.warning_count > 0:
                    status = "warning"
                else:
                    status = "passed"

                summary = {
                    "cluster_name": result.cluster_name,
                    "inspection_type": result.inspection_type,
                    "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                    "result_id": result.result_id,
                    "total": result.total_items,
                    "passed": result.passed_count,
                    "critical": result.critical_count,
                    "warning": result.warning_count,
                    "info": result.info_count,
                    "status": status,
                }
                summaries.append(summary)

            return {
                "results": summaries,
                "total": total_count,
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            logger.error(f"Failed to list results: {e}")
            raise

    async def save_result(self, result_data: Dict[str, Any]) -> str:
        """Save inspection result"""
        try:
            # Extract statistics from summary (new format)
            summary = result_data["summary"]
            total_items = summary.get("total_items", 0)
            passed_count = summary.get("passed", 0)
            critical_count = summary.get("failed", 0)  # failed maps to critical
            warning_count = summary.get("warning", 0)
            info_count = summary.get("error", 0)  # error maps to info

            # Create database record
            create_data = {
                "result_id": result_data["result_id"],
                "cluster_name": result_data["cluster_name"],
                "inspection_type": result_data["inspection_type"],
                # Remove timestamp to let database use default value
                "total_items": total_items,
                "passed_count": passed_count,
                "critical_count": critical_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "result_data": result_data,
                "execution_duration": result_data.get("execution_info", {}).get("execution_duration"),
                "triggered_by": result_data.get("execution_info", {}).get("triggered_by", "user"),
                "inspectors_used": result_data.get("execution_info", {}).get("inspectors_used", []),
            }

            result = await self.create(create_data)

            # Invalidate cache for this cluster to ensure fresh data
            cluster_name = result_data["cluster_name"]
            invalidate_cache("inspection_results")

            return result.result_id
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            raise

    async def delete_by_result_id(self, result_id: str) -> bool:
        """Delete result by result_id"""
        try:
            deleted = await self.get_by_field_and_delete("result_id", result_id)
            if deleted:
                # Invalidate cache for this cluster
                invalidate_cache("inspection_results")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete result {result_id}: {e}")
            raise

    @cached("inspection_results", maxsize=100, ttl=300)
    async def get_latest_by_cluster(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """Get latest result for cluster with TTL caching"""
        try:
            # Query database
            stmt = (
                select(InspectionResult)
                .where(InspectionResult.cluster_name == cluster_name)
                .order_by(desc(InspectionResult.timestamp))
                .limit(1)
            )

            result = await self.session.execute(stmt)
            inspection_result = result.scalar_one_or_none()

            return inspection_result.result_data if inspection_result else None
        except Exception as e:
            logger.error(f"Failed to get latest result for cluster {cluster_name}: {e}")
            raise

    async def get_latest_results_for_all_clusters(
        self, cluster_names: List[str], exclude_inspection_types: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get latest inspection results for multiple clusters in a single query.

        This method uses a window function to get the latest result for each cluster,
        avoiding N+1 query problems when fetching results for multiple clusters.

        Args:
            cluster_names: List of cluster names to fetch results for
            exclude_inspection_types: Optional list of inspection types to exclude

        Returns:
            Dict[str, Dict[str, Any]]: Mapping of cluster_name to latest result_data
        """
        try:
            if not cluster_names:
                return {}

            # Build where conditions
            conditions = [InspectionResult.cluster_name.in_(cluster_names)]
            if exclude_inspection_types:
                conditions.append(InspectionResult.inspection_type.notin_(exclude_inspection_types))

            # Use subquery to get latest timestamp for each cluster
            subquery = (
                select(
                    InspectionResult.cluster_name,
                    func.max(InspectionResult.timestamp).label("max_timestamp"),
                )
                .where(and_(*conditions))
                .group_by(InspectionResult.cluster_name)
                .subquery()
            )

            # Get latest results for each cluster
            stmt = select(InspectionResult).join(
                subquery,
                (InspectionResult.cluster_name == subquery.c.cluster_name)
                & (InspectionResult.timestamp == subquery.c.max_timestamp),
            )

            result = await self.session.execute(stmt)
            inspection_results = result.scalars().all()

            # Build dictionary: cluster_name -> result_data
            return {r.cluster_name: r.result_data for r in inspection_results}
        except Exception as e:
            logger.error(f"Failed to get latest results for clusters: {e}")
            raise
