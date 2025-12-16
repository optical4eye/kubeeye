from datetime import datetime
from typing import Dict

# Import existing utilities
from infrastructure.cluster.cluster_config import (
    list_clusters,
    get_cluster,
    get_cluster_status_counts_fast,
    get_cluster_quick_status,
)
from infrastructure.results.inspection_result import (
    list_results,
    get_latest_result_by_cluster,
)
from infrastructure.rules.rule_loader import load_rules
from infrastructure.gitops.gitops_manager import GitOpsRuleManager
from infrastructure.security.cert_checker import get_cluster_cert_status
import logging

logger = logging.getLogger(__name__)


def get_dashboard_data_api() -> Dict:
    """Get dashboard data for API (without Streamlit dependencies)"""

    # Fast cluster loading
    clusters = list_clusters()
    total_clusters = len(clusters)

    # Debug logging
    logger.debug(f"get_dashboard_data_api - clusters loaded: {len(clusters)}")
    if clusters:
        logger.debug(f"clusters: {clusters}")

    # Load rules
    node_rules = load_rules("node")
    prometheus_rules = load_rules("prometheus")
    opa_rules = load_rules("opa")
    total_rules = len(node_rules) + len(prometheus_rules) + len(opa_rules)

    # Check if GitOps is configured and add GitOps rules
    gitops_manager = GitOpsRuleManager()
    gitops_config = gitops_manager.load_config()
    if gitops_config.get("mode") == "gitops" and gitops_config.get("repository"):
        try:
            gitops_rules = gitops_manager.get_repo_rules(gitops_config["repository"]["name"])
            total_rules += len(gitops_rules)
        except Exception as e:
            logger.warning(f"Failed to load GitOps rules: {e}")

    # Fast status counting without loading all results
    status_counts = get_cluster_status_counts_fast()

    # Load results for dashboard (increased for trends)
    recent_results = list_results(limit=100, order_by="timestamp DESC")

    # Recent scans statistics (24 hours)
    now = datetime.now()
    cutoff_time = now.timestamp() - (24 * 3600)

    recent_scans = 0
    recent_issues = 0

    for result in recent_results:
        timestamp = datetime.fromisoformat(result["timestamp"]).timestamp()
        if timestamp > cutoff_time:
            recent_scans += 1
            recent_issues += result.get("critical", 0) + result.get("warning", 0)

    # Last inspection time
    latest_scan_time = "No data"
    if recent_results:
        latest_time = datetime.fromisoformat(recent_results[0]["timestamp"])
        latest_scan_time = latest_time.strftime("%m-%d %H:%M")

    # Create simplified cluster statuses (only necessary fields)
    cluster_statuses = []
    for cluster_name in clusters:
        try:
            # Fast status check
            status = get_cluster_quick_status(cluster_name)
            latest_result = get_latest_result_by_cluster(cluster_name)

            # Get node and certificate information
            node_count = 0
            cert_status = "unknown"
            cert_days_remaining = None
            try:
                cluster_config = get_cluster(cluster_name)
                nodes = cluster_config.get_nodes()
                node_count = len(nodes) if nodes else 0

                kubeconfig_content = cluster_config.get_kubeconfig()
                if kubeconfig_content:
                    cert_info = get_cluster_cert_status(cluster_name, kubeconfig_content)
                    cert_status = cert_info.get("status", "unknown")
                    cert_days_remaining = cert_info.get("days_remaining")
            except Exception as e:
                logger.warning(f"Failed to get information for cluster {cluster_name}: {e}")
                cert_status = "unknown"
                cert_days_remaining = None

            cluster_status_dict = {
                "name": cluster_name,
                "status": status,
                "last_scan": latest_result["timestamp"] if latest_result else None,
                "critical_count": (latest_result.get("critical", 0) if latest_result else 0),
                "warning_count": (latest_result.get("warning", 0) if latest_result else 0),
                "passed_count": latest_result.get("passed", 0) if latest_result else 0,
                "node_count": node_count,
                "cert_status": cert_status,
                "cert_days_remaining": cert_days_remaining,
            }

            cluster_statuses.append(cluster_status_dict)
        except Exception as e:
            # In case of error - minimal information
            logger.warning(f"Error processing cluster {cluster_name}: {e}")
            cluster_statuses.append(
                {
                    "name": cluster_name,
                    "status": "unknown",
                    "last_scan": None,
                    "critical_count": 0,
                    "warning_count": 0,
                    "passed_count": 0,
                    "node_count": 0,
                    "cert_status": "unknown",
                    "cert_days_remaining": None,
                }
            )

    return {
        "clusters": clusters,
        "cluster_statuses": cluster_statuses,
        "total_clusters": total_clusters,
        "recent_scans": recent_scans,
        "recent_issues": recent_issues,
        "latest_scan_time": latest_scan_time,
        "total_rules": total_rules,
        "status_counts": status_counts,
        "recent_results": recent_results,
    }
