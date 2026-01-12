#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database model for clusters
"""

from sqlalchemy import Column, String, Text, JSON, Index, Integer, ForeignKey
from sqlalchemy.orm import relationship
from db.models.base import BaseModel


class Cluster(BaseModel):
    """Database model for clusters"""

    __tablename__ = "clusters"

    # Core identification
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Node configurations (stored as JSON)
    nodes = Column(JSON, nullable=False, default=list)

    # Kubernetes configuration
    kubeconfig = Column(Text, nullable=True)  # Base64 encoded, encrypted in production

    # Secret references (optional - for using stored secrets)
    password_secret_id = Column(Integer, ForeignKey("secrets.id"), nullable=True)
    ssh_key_secret_id = Column(Integer, ForeignKey("secrets.id"), nullable=True)
    kubeconfig_secret_id = Column(Integer, ForeignKey("secrets.id"), nullable=True)

    # Relationships
    password_secret = relationship("Secret", foreign_keys=[password_secret_id], backref="password_clusters")
    ssh_key_secret = relationship("Secret", foreign_keys=[ssh_key_secret_id], backref="ssh_key_clusters")
    kubeconfig_secret = relationship("Secret", foreign_keys=[kubeconfig_secret_id], backref="kubeconfig_clusters")

    # Status tracking
    last_inspection = Column(String(255), nullable=True)  # result_id of last inspection
    status = Column(String(50), default="unknown")  # healthy, warning, critical, unknown

    # Indexes
    __table_args__ = (
        Index("idx_clusters_status", "status"),
        Index("idx_clusters_last_inspection", "last_inspection"),
        Index("idx_clusters_name_status", "name", "status"),  # For filtering by name and status
        Index("idx_clusters_created_at", "created_at"),  # For ordering by creation time
        Index("idx_clusters_updated_at", "updated_at"),  # For ordering by update time
    )

    @staticmethod
    def validate_data(data: dict) -> dict:
        """Validate cluster data before creation/update"""
        if "name" in data and not data.get("name"):
            raise ValueError("Cluster name is required")
        if "name" in data and (not isinstance(data["name"], str) or len(data["name"]) > 255):
            raise ValueError("Cluster name must be a string with max length 255")

        # Validate nodes if provided
        if "nodes" in data:
            nodes = data["nodes"]
            if not isinstance(nodes, list):
                raise ValueError("Nodes must be a list")
            for node in nodes:
                if not isinstance(node, dict):
                    raise ValueError("Each node must be a dictionary")

        # Validate kubeconfig if provided
        if "kubeconfig" in data:
            kubeconfig = data["kubeconfig"]
            if kubeconfig is not None and not isinstance(kubeconfig, str):
                raise ValueError("Kubeconfig must be a string or None")

        return data

    def __repr__(self):
        return f"<Cluster(name='{self.name}', status='{self.status}')>"
