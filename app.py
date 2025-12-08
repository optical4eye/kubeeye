#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye - Kubernetes cluster inspection tool


This file is the application entry point, initializes the interface and displays the main page content.
"""


# Import standard libraries
from datetime import datetime
from typing import Dict

# Import third-party libraries
import streamlit as st
import pandas as pd
import plotly.express as px


# Page configuration setup - must be the first Streamlit command
st.set_page_config(
    page_title="KubeEye - Kubernetes cluster inspection tool",
    layout="wide"
)


# Import project modules
from utils.common import initialize_page
from utils.cluster_config import list_clusters, get_cluster, get_cluster_status_counts_fast, get_cluster_quick_status
from utils.inspection_result import list_results, get_latest_result_by_cluster
from utils.rule_loader import load_rules
from utils.gitops_manager import GitOpsRuleManager
from utils.version import VERSION
from utils.cert_checker import get_cluster_cert_status
import logging

logger = logging.getLogger(__name__)


# Page initialization
initialize_page(
    title="KubeEye",
    page_title="Cluster overview",
    page_subtitle="Monitoring and inspection of Kubernetes clusters"
)


# Optimized dashboard loading with limited data
@st.cache_data(ttl=60)  # Cache for 1 minute for fast updates
def get_dashboard_data() -> Dict:
    """Fast dashboard loading with limited data"""

    # Fast cluster loading
    clusters = list_clusters()
    total_clusters = len(clusters)

    # Debug inside function
    print(f"DEBUG: get_dashboard_data - clusters loaded: {len(clusters)}")
    if clusters:
        print(f"DEBUG: clusters: {clusters}")

    # Load rules
    node_rules = load_rules('node')
    prometheus_rules = load_rules('prometheus')
    opa_rules = load_rules('opa')
    total_rules = len(node_rules) + len(prometheus_rules) + len(opa_rules)

    # Check if GitOps is configured and add GitOps rules
    gitops_manager = GitOpsRuleManager()
    gitops_config = gitops_manager.load_config()
    if gitops_config.get('mode') == 'gitops' and gitops_config.get('repository'):
        try:
            gitops_rules = gitops_manager.get_repo_rules(gitops_config['repository']['name'])
            total_rules += len(gitops_rules)
        except Exception as e:
            print(f"Warning: Failed to load GitOps rules: {e}")

    # Fast status counting without loading all results
    status_counts = get_cluster_status_counts_fast()

    # Load results for dashboard (increased for trends)
    recent_results = list_results(limit=100, order_by='timestamp DESC')

    # Recent scans statistics (24 hours)
    now = datetime.now()
    cutoff_time = now.timestamp() - (24 * 3600)

    recent_scans = 0
    recent_issues = 0

    for result in recent_results:
        timestamp = datetime.fromisoformat(result['timestamp']).timestamp()
        if timestamp > cutoff_time:
            recent_scans += 1
            recent_issues += result.get('critical', 0) + result.get('warning', 0)

    # Last inspection time
    latest_scan_time = "No data"
    if recent_results:
        latest_time = datetime.fromisoformat(recent_results[0]['timestamp'])
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
            cert_status = 'unknown'
            cert_days_remaining = None
            try:
                cluster_config = get_cluster(cluster_name)
                nodes = cluster_config.get_nodes()
                node_count = len(nodes) if nodes else 0

                kubeconfig_content = cluster_config.get_kubeconfig()
                if kubeconfig_content:
                    cert_info = get_cluster_cert_status(cluster_name, kubeconfig_content)
                    cert_status = cert_info.get('status', 'unknown')
                    cert_days_remaining = cert_info.get('days_remaining')
            except Exception as e:
                logger.warning(f"Failed to get information for cluster {cluster_name}: {e}")
                cert_status = 'unknown'
                cert_days_remaining = None

            cluster_status_dict = {
                'name': cluster_name,
                'status': status,
                'last_scan': latest_result['timestamp'] if latest_result else None,
                'critical_count': latest_result.get('critical', 0) if latest_result else 0,
                'warning_count': latest_result.get('warning', 0) if latest_result else 0,
                'passed_count': latest_result.get('passed', 0) if latest_result else 0,
                'node_count': node_count,
                'cert_status': cert_status,
                'cert_days_remaining': cert_days_remaining
            }

            cluster_statuses.append(cluster_status_dict)
        except Exception as e:
            # In case of error - minimal information
            logger.warning(f"Error processing cluster {cluster_name}: {e}")
            cluster_statuses.append({
                'name': cluster_name,
                'status': 'unknown',
                'last_scan': None,
                'critical_count': 0,
                'warning_count': 0,
                'passed_count': 0,
                'node_count': 0,
                'cert_status': 'unknown',
                'cert_days_remaining': None
            })

    return {
        'clusters': clusters,
        'cluster_statuses': cluster_statuses,
        'total_clusters': total_clusters,
        'recent_scans': recent_scans,
        'recent_issues': recent_issues,
        'latest_scan_time': latest_scan_time,
        'total_rules': total_rules,
        'status_counts': status_counts,
        'recent_results': recent_results
    }


# Caching disabled for dashboard

# Clear cache on first page load (if parameter exists)
if st.query_params.get("clear_cache") == "true":
    get_dashboard_data.clear()
    st.query_params.clear()

# Restore get_dashboard_data() call with error handling
try:
    dashboard_data = get_dashboard_data()


except Exception as e:
    st.error(f"Dashboard data loading error: {str(e)}")
    # Load minimal data for operation
    from utils.cluster_config import list_clusters
    clusters = list_clusters()
    dashboard_data = {
        'clusters': clusters,
        'cluster_statuses': [{'name': c, 'status': 'unknown', 'last_scan': None, 'critical_count': 0, 'warning_count': 0, 'passed_count': 0, 'node_count': 0, 'cert_status': 'unknown', 'cert_days_remaining': None} for c in clusters],
        'total_clusters': len(clusters),
        'recent_scans': 0,
        'recent_issues': 0,
        'latest_scan_time': "Loading error",
        'total_rules': 0,
        'status_counts': {'healthy': 0, 'warning': 0, 'critical': 0, 'unknown': len(clusters) if clusters else 0},
        'recent_results': []
    }

# Helper functions for error counting
def count_errors_from_items(items):
    """Centralized function for counting errors by items"""
    critical = 0
    warning = 0
    passed = 0

    for item in items:
        if isinstance(item, dict):
            status = item.get('status', 'unknown')
            severity = item.get('severity', 'unknown')

            if status == 'passed':
                passed += 1
            elif status == 'exception':
                if severity == 'critical':
                    critical += 1
                elif severity == 'warning':
                    warning += 1
                # 'info' and other severity not counted in main counters

    return {'critical': critical, 'warning': warning, 'passed': passed}

def count_errors_from_result(result_data):
    """Count errors from saved result data"""
    # For dashboard: count all non-critical errors as warnings
    critical = result_data.get('critical', 0)
    warning = result_data.get('warning', 0)
    passed = result_data.get('passed', 0)

    # In dashboard "warnings" include all non-critical errors
    # (warning + info + error severity)
    # But since we only store critical/warning/passed,
    # assume that all non-critical and non-warning are other error types
    # For now leave as is - only 'warning' severity
    return {
        'critical': critical,
        'warning': warning,
        'passed': passed
    }

# Minimalist styles
st.markdown("""
<style>
/* Only necessary styles for readability */
.stDataFrame { font-size: 14px; }
.stMetric { font-size: 16px; }

/* Responsive for mobile */
@media (max-width: 768px) {
    .stDataFrame { font-size: 12px; }
    .stMetric { font-size: 14px; }
}
</style>
""", unsafe_allow_html=True)

# Toast notifications for successful operations
def show_toast(message, type="success"):
    toast_js = f"""
    <script>
    if (window.showToast) {{
        window.showToast("{message}", "{type}");
    }}
    </script>
    """
    st.markdown(toast_js, unsafe_allow_html=True)


# Unpacking data from optimized structure
clusters = dashboard_data['clusters']
cluster_statuses = {cs['name']: cs for cs in dashboard_data['cluster_statuses']}

total_clusters = dashboard_data['total_clusters']
recent_scans = dashboard_data['recent_scans']
recent_issues = dashboard_data['recent_issues']
latest_scan_time = dashboard_data['latest_scan_time']
total_rules = dashboard_data['total_rules']
status_counts = dashboard_data['status_counts']
recent_results = dashboard_data['recent_results']

# Enhanced cluster status diagram (linked to reports)
status_labels = {
    'healthy': 'Passed',
    'warning': 'Warnings',
    'critical': 'Critical errors',
    'unknown': 'Unknown'
}
status_colors = {
    'healthy': '#10B981',    # Green for passed (as in reports)
    'warning': '#F59E0B',    # Orange for regular errors (as in reports)
    'critical': '#EF4444',   # Red for critical errors (as in reports)
    'unknown': '#6B7280'     # Gray for unknown
}

# Create a donut chart with numbers
fig_pie = px.pie(
    values=list(status_counts.values()),
    names=[f"{status_labels[k]} ({count})" for k, count in status_counts.items()],
    title="Cluster status distribution",
    color=[status_labels[k] for k in status_counts.keys()],
    color_discrete_map=status_colors,
    hole=0.4  # Donut chart
)

# Enhanced display settings
fig_pie.update_traces(
    textposition='inside',
    textinfo='percent+value',
    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>',
    marker=dict(line=dict(color='white', width=2))
)

# Add total count in the center
total_clusters = sum(status_counts.values())
fig_pie.add_annotation(
    text=f"<b>{total_clusters}</b><br>clusters",
    x=0.5, y=0.5, showarrow=False,
    font=dict(size=16, color='#1f2937'),
    bgcolor='rgba(255,255,255,0.9)',
    bordercolor='#d1d5db',
    borderwidth=1,
    borderpad=4
)

# Enhanced legend
fig_pie.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.15,
        xanchor="center",
        x=0.5,
        font=dict(size=12)
    ),
    margin=dict(t=50, b=100, l=50, r=50)
)


# Main metrics
st.markdown("## Overview")

# Dashboard data refresh button
col_refresh, col_spacer = st.columns([1, 5])
with col_refresh:
    if st.button("Refresh data", type="primary", help="Refresh dashboard data"):
        get_dashboard_data.clear()  # Clear cache before refresh
        st.rerun()

# Preparing data for metrics
latest_scan_display = dashboard_data['latest_scan_time'] if dashboard_data['latest_scan_time'] != "Never started" else "No"

# Calculation of recent issues by types (as in report details)
now = datetime.now()
cutoff_time = now.timestamp() - (24 * 3600)  # 24 hours ago

recent_critical = 0
recent_warnings = 0
recent_info = 0
for result in recent_results:
    timestamp = datetime.fromisoformat(result['timestamp']).timestamp()
    if timestamp > cutoff_time:
        recent_critical += result.get('critical', 0)
        recent_warnings += result.get('warning', 0)
        recent_info += result.get('info', 0)  # Add info error count

# Simple metrics in columns (expand to 7 columns)
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    cluster_count = dashboard_data['total_clusters']
    st.metric("Clusters", cluster_count)
with col2:
    st.metric("Inspections", dashboard_data['recent_scans'])
with col3:
    st.metric("Critical", recent_critical)
with col4:
    st.metric("Warnings", recent_warnings)
with col5:
    st.metric("Other", recent_info)
with col6:
    st.metric("Latest", latest_scan_display)
with col7:
    st.metric("Rules", dashboard_data['total_rules'])


# Error trends over the last 7 days
st.markdown("### Error trends (7 days)")

# Preparing data for time series
if recent_results:
    # Grouping data by days
    from collections import defaultdict
    daily_errors = defaultdict(lambda: {'critical': 0, 'warning': 0, 'info': 0, 'total': 0})

    cutoff_7d = now.timestamp() - (7 * 24 * 3600)  # 7 days ago

    for result in recent_results:
        timestamp = datetime.fromisoformat(result['timestamp']).timestamp()
        if timestamp > cutoff_7d:
            date_key = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            daily_errors[date_key]['critical'] += result.get('critical', 0)
            daily_errors[date_key]['warning'] += result.get('warning', 0)
            daily_errors[date_key]['info'] += result.get('info', 0)
            daily_errors[date_key]['total'] += (result.get('critical', 0) + result.get('warning', 0) + result.get('info', 0))

    # Creating DataFrame for chart
    if daily_errors:
        dates = sorted(daily_errors.keys())
        critical_vals = [daily_errors[d]['critical'] for d in dates]
        warning_vals = [daily_errors[d]['warning'] for d in dates]
        info_vals = [daily_errors[d]['info'] for d in dates]

        # Creating DataFrame for better display
        trend_data = []
        for i, date in enumerate(dates):
            trend_data.extend([
                {'date': date, 'errors': critical_vals[i], 'type': 'Critical'},
                {'date': date, 'errors': warning_vals[i], 'type': 'Warnings'},
                {'date': date, 'errors': info_vals[i], 'type': 'Other'}
            ])

        df_trend = pd.DataFrame(trend_data)

        # Line chart for trends
        fig_trend = px.line(
            df_trend,
            x='date',
            y='errors',
            color='type',
            title="Error dynamics by day",
            markers=True,
            color_discrete_map={
                'Critical': '#EF4444',    # Red
                'Warnings': '#F59E0B', # Orange
                'Other': '#6B7280'          # Gray
            }
        )

        fig_trend.update_layout(
            xaxis_title="Date",
            yaxis_title="Error count",
            legend_title="Error type",
            hovermode="x unified",
            xaxis=dict(showgrid=True, gridcolor='#acacac'),
            yaxis=dict(showgrid=True, gridcolor='#acacac')
        )

        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Insufficient data to display trends (need inspection results for the last 7 days)")
else:
    st.info("No data to display trends")


# Display bar chart with side statistics panel
col1, col2 = st.columns([2, 1])

with col1:
        # Bar chart - display total number of checks by types
        # Count total number of checks by types from all clusters
        total_critical = sum(cs.get('critical_count', 0) for cs in dashboard_data['cluster_statuses'])
        total_warnings = sum(cs.get('warning_count', 0) for cs in dashboard_data['cluster_statuses'])
        total_passed = sum(cs.get('passed_count', 0) for cs in dashboard_data['cluster_statuses'])

        # Order: critical errors, warnings, passed
        issue_labels = ['Critical errors', 'Warnings', 'Passed']
        issue_values = [total_critical, total_warnings, total_passed]
        issue_colors = ['#EF4444', '#F59E0B', '#10B981']  # Red, orange, green

        fig_bar = px.bar(
            x=issue_labels,
            y=issue_values,
            title="Inspection results distribution",
            color=issue_labels,
            color_discrete_map=dict(zip(issue_labels, issue_colors)),
            text_auto=True
        )
        fig_bar.update_layout(
            xaxis_title="Result type",
            yaxis_title="Check count",
            showlegend=False,
            xaxis=dict(showgrid=True, gridcolor='#acacac'),
            yaxis=dict(showgrid=True, gridcolor='#acacac')
        )
        # Enhanced hover for bar chart
        fig_bar.update_traces(
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with col2:
        st.markdown("### Statistics")

        # Count total number of errors from all clusters (use centralized function)
        total_critical_issues = 0
        total_warning_issues = 0
        total_passed_issues = 0

        for cs in dashboard_data['cluster_statuses']:
            # Use centralized counting function
            counts = count_errors_from_result({
                'critical': cs.get('critical_count', 0),
                'warning': cs.get('warning_count', 0),
                'passed': cs.get('passed_count', 0)
            })
            total_critical_issues += counts['critical']
            total_warning_issues += counts['warning']
            total_passed_issues += counts['passed']

        # Key metrics - total number of errors (always display)
        st.error(f"Critical errors: {total_critical_issues}")
        st.warning(f"Warnings: {total_warning_issues}")
        st.success(f"Passed: {total_passed_issues}")

        # Clusters by statuses with names
        if dashboard_data['cluster_statuses']:
            st.markdown("**Clusters by status:**")

            # Group clusters by statuses
            clusters_by_status = {
                'critical': [],
                'warning': [],
                'healthy': [],
                'unknown': []
            }

            for cs in dashboard_data['cluster_statuses']:
                status = cs.get('status', 'unknown')
                if status in clusters_by_status:
                    clusters_by_status[status].append(cs['name'])

            # Display clusters by statuses
            status_display = {
                'critical': ('Critical errors', '#EF4444'),
                'warning': ('Warnings', '#F59E0B'),
                'healthy': ('Passed', '#10B981'),
                'unknown': ('Unknown', '#6B7280')
            }

            for status_key, (label, color) in status_display.items():
                clusters = clusters_by_status[status_key]
                if clusters:
                    with st.expander(f"{label} ({len(clusters)})", expanded=False):
                        for cluster_name in sorted(clusters):
                            st.write(f"• {cluster_name}")

            # Additionally show clusters with warnings
            clusters_with_warnings = []
            for cs in dashboard_data['cluster_statuses']:
                if cs.get('warning_count', 0) > 0:
                    clusters_with_warnings.append(cs['name'])

            if clusters_with_warnings:
                with st.expander(f"Warnings ({len(clusters_with_warnings)})", expanded=False):
                    for cluster_name in sorted(clusters_with_warnings):
                        st.write(f"• {cluster_name}")


        # Additional information
        st.markdown("---")
        st.caption(f"Total clusters: {total_clusters}")
        st.caption(f"Updated: {datetime.now().strftime('%H:%M')}")

st.markdown("---")


# Cluster details
st.markdown("## Cluster details")

# Search for clusters
search_term = st.text_input("Search clusters", placeholder="Enter cluster name...")

if not dashboard_data.get('clusters', []):
    st.warning("Cluster configuration is missing. Add clusters on the cluster info page.")
    if st.button("Add cluster", type="primary"):
        st.switch_page("pages/1_cluster_info.py")
else:
    # Simplified cluster table
    cluster_data = []
    for cluster_status in dashboard_data['cluster_statuses']:
        # Simplified statuses without emoji
        status_map = {
            'healthy': 'Healthy',
            'warning': 'Warning',
            'critical': 'Critical',
            'unknown': 'Unknown'
        }

        cert_status_map = {
            'valid': 'Valid',
            'warning': 'Expires soon',
            'critical': 'Close to expiration',
            'expired': 'Expired',
            'unknown': 'Unknown'
        }

        cert_display = cert_status_map.get(cluster_status['cert_status'], 'Unknown')
        if cluster_status['cert_days_remaining'] is not None:
            cert_display += f" ({cluster_status['cert_days_remaining']} d.)"

        last_scan = "Not checked"
        if cluster_status['last_scan']:
            # Convert timestamp string back to datetime for formatting
            last_scan_dt = datetime.fromisoformat(cluster_status['last_scan'])
            last_scan = last_scan_dt.strftime("%m-%d %H:%M")

        cluster_data.append({
            "Cluster": cluster_status['name'],
            "Status": status_map[cluster_status['status']],
            "Nodes": cluster_status['node_count'],
            "Certificate": cert_display,
            "Last check": last_scan,
            "Critical": cluster_status['critical_count'],
            "Warnings": cluster_status['warning_count']
        })

    # Filtering
    if search_term:
        cluster_data = [row for row in cluster_data if search_term.lower() in row["Cluster"].lower()]

    if cluster_data:
        cluster_df = pd.DataFrame(cluster_data)
        st.dataframe(
            cluster_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Cluster": st.column_config.TextColumn("Cluster", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Nodes": st.column_config.NumberColumn("Nodes", width="small"),
                "Certificate": st.column_config.TextColumn("Certificate", width="medium"),
                "Last check": st.column_config.TextColumn("Last check", width="medium"),
                "Critical": st.column_config.NumberColumn("Critical", width="small"),
                "Warnings": st.column_config.NumberColumn("Warnings", width="small")
            }
        )
    else:
        st.info("Clusters not found")

    # Quick actions
    st.markdown("### Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Run inspection", type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")

    with col2:
        if st.button("View report", type="primary"):
            st.switch_page("pages/3_inspect_report.py")

    with col3:
        if st.button("Cluster management", type="primary"):
            st.switch_page("pages/1_cluster_info.py")


# Recent checks
st.markdown("## Recent checks")

if recent_results:
    scan_records = []
    for result in recent_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")

        critical = result.get('critical', 0)
        warning = result.get('warning', 0)

        if critical > 0:
            status = 'Critical'
        elif warning > 0:
            status = 'Warning'
        else:
            status = 'OK'

        scan_records.append({
            "Time": time_str,
            "Cluster": result['cluster_name'],
            "Type": result['inspection_type'],
            "Status": status,
            "Critical": critical,
            "Warnings": warning
        })

    scan_df = pd.DataFrame(scan_records)
    st.dataframe(scan_df, use_container_width=True, hide_index=True)
else:
    st.info("Inspection records are missing")


# Footer
st.markdown("---")
st.caption(f"KubeEye {VERSION} | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
