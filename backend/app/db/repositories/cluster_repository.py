#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository for cluster operations - Async Only
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.repositories.base_repository import BaseRepository
from db.models.cluster import Cluster
from core.common.cache_utils import cached
from core.logging import get_logger

logger = get_logger(__name__)


class ClusterRepository(BaseRepository[Cluster]):
    """Async repository for cluster operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Cluster)

    @cached("clusters", ttl=600)
    async def get_by_name(self, name: str) -> Optional[Cluster]:
        """Get cluster by name"""
        cluster = await self.get_by_field("name", name)
        if cluster:
            logger.info(f"Found cluster {name}")
        else:
            logger.warning(f"Cluster {name} not found")
        return cluster

    async def get_all_names(self) -> List[str]:
        """Get all cluster names"""
        try:
            stmt = select(Cluster.name)
            result = await self.session.execute(stmt)
            names = [name for (name,) in result.all()]
            logger.info(f"Retrieved {len(names)} cluster names")
            return names
        except Exception as e:
            logger.error(f"Failed to get all cluster names: {e}")
            raise

    async def get_all_clusters_with_details(self) -> List[Cluster]:
        """
        Get all clusters with all related details loaded in a single query.

        This method uses selectinload to avoid N+1 query problems by loading
        related entities (password_secret, ssh_key_secret, kubeconfig_secret)
        in a single query. Note: nodes are stored as JSON and are loaded automatically.

        Returns:
            List[Cluster]: List of clusters with all related details loaded
        """
        stmt = select(Cluster).options(
            selectinload(Cluster.password_secret),
            selectinload(Cluster.ssh_key_secret),
            selectinload(Cluster.kubeconfig_secret),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_cluster(
        self, name: str, nodes: Optional[List[Dict]] = None, kubeconfig: Optional[str] = None
    ) -> Cluster:
        """Create new cluster"""
        create_data = {
            "name": name,
            "nodes": nodes or [],
            "kubeconfig": kubeconfig or "",
        }
        cluster = await self.create(create_data)
        logger.info(f"Created cluster {name} with {len(nodes or [])} nodes")
        return cluster

    async def update_cluster(self, name: str, **kwargs) -> Optional[Cluster]:
        """Update cluster by name"""
        try:
            # Handle special fields
            update_data = {}
            if "nodes" in kwargs:
                update_data["nodes"] = kwargs.pop("nodes")

            if "kubeconfig" in kwargs:
                kubeconfig = kwargs.pop("kubeconfig")
                # Handle case where kubeconfig might be stored as a dict
                if isinstance(kubeconfig, dict):
                    kubeconfig = kubeconfig.get("kubeconfig", "")
                update_data["kubeconfig"] = kubeconfig if isinstance(kubeconfig, str) else ""

            # Add other fields
            update_data.update(kwargs)

            # Update using unified base repository method
            updated_cluster = await self.get_by_field_and_update("name", name, update_data)
            if updated_cluster:
                logger.info(f"Updated cluster {name}")
            return updated_cluster
        except Exception as e:
            logger.error(f"Failed to update cluster {name}: {e}")
            raise

    async def delete_cluster(self, name: str) -> bool:
        """Delete cluster by name"""
        try:
            deleted = await self.get_by_field_and_delete("name", name)
            if deleted:
                logger.info(f"Deleted cluster {name}")
            else:
                logger.warning(f"Cluster {name} not found for deletion")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete cluster {name}: {e}")
            raise

    async def get_cluster_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get cluster configuration in dict format (compatible with existing code)"""
        try:
            cluster = await self.get_by_name(name)
            if not cluster:
                return None

            config = {
                "name": cluster.name,
                "nodes": cluster.nodes or [],
                "kubeconfig": cluster.kubeconfig or "",
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
                "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else None,
            }

            # Add structured data for inspectors
            config.update(
                {
                    "kubeconfig": {"kubeconfig": config["kubeconfig"]},
                    "opa": {"kubeconfig": config["kubeconfig"]},
                }
            )

            logger.debug(f"Retrieved cluster config for {name} with {len(config.get('nodes', []))} nodes")
            return config
        except Exception as e:
            logger.error(f"Failed to get cluster config for {name}: {e}")
            raise

    async def update_last_inspection(self, name: str, result_id: str, status: str) -> bool:
        """Update last inspection info"""
        try:
            updated = await self.get_by_field_and_update("name", name, {"last_inspection": result_id, "status": status})
            if updated:
                logger.info(f"Updated last inspection for cluster {name}: {result_id}, status: {status}")
            else:
                logger.warning(f"Cluster {name} not found for inspection update")
            return updated is not None
        except Exception as e:
            logger.error(f"Failed to update last inspection for {name}: {e}")
            raise
