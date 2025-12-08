#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes cluster inspection reports page - reworked version
Providing improved user experience and clearer report management interface
"""


import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import sys
from pathlib import Path
from typing import Dict
import time
from functools import wraps

def timing_decorator(func):
    """Decorator for measuring function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time
        if execution_time > 1.0:  # Log only slow operations
            st.info(f"{func.__name__} executed in {execution_time:.2f} sec")

        return result
    return wrapper

# Page setup
st.set_page_config(
    page_title="Inspection reports - kubeeye",
    layout="wide"
)


# Minimalist styles
st.markdown("""
<style>
.stDataFrame { font-size: 14px; }
.stButton > button { padding: 6px 12px; }
</style>
""", unsafe_allow_html=True)


# Add project root directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Import utilities
from utils.common import initialize_page
from utils.cluster_config import list_clusters
from utils.inspection_result import list_results, load_result
from components.ui.result_display import display_inspection_results
from components.ui.result_display import parse_opa_violations_to_table, display_opa_violations_table

# Configuration for report cleanup
CONFIG_FILE = Path(__file__).parent.parent / "data" / "cleanup_config.json"
DEFAULT_RETENTION_DAYS = 14
DEFAULT_AUTO_CLEANUP = False

# Environment variable for retention days
ENV_RETENTION_DAYS = "KUBEYE_REPORT_RETENTION_DAYS"

def load_cleanup_config() -> dict:
    """Load cleanup configuration"""
    # Check environment variable first
    env_retention = os.getenv(ENV_RETENTION_DAYS)
    if env_retention:
        try:
            retention_days = int(env_retention)
            if retention_days > 0:
                return {
                    'retention_days': retention_days,
                    'source': 'env'
                }
        except ValueError:
            pass

    # Fall back to config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config['source'] = 'file'
                return config
        except Exception:
            pass

    return {
        'retention_days': DEFAULT_RETENTION_DAYS,
        'source': 'default'
    }

def save_cleanup_config(config: dict):
    """Save cleanup configuration"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def safe_display_opa_violations_table(violations_data, show_expander=False, table_key=None):
    """Safe call to display_opa_violations_table function considering parameter compatibility"""
    try:
        if table_key:
            return display_opa_violations_table(violations_data, show_expander=show_expander, table_key=table_key)
        else:
            return display_opa_violations_table(violations_data, show_expander=show_expander)
    except TypeError:
        return display_opa_violations_table(violations_data, show_expander=show_expander)


def cleanup_old_reports(retention_days: int) -> tuple[int, int]:
    """Clean up old reports older than retention_days days

    Returns:
        tuple: (deleted_files, freed_space_in_bytes)
    """
    if retention_days <= 0:
        return 0, 0

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    results_dir = Path(__file__).parent.parent / "data" / "results"

    if not results_dir.exists():
        return 0, 0

    deleted_count = 0
    freed_space = 0

    for file_path in results_dir.glob("*.json"):
        try:
            # Check file modification date
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_date:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                freed_space += file_size
        except Exception:
            continue

    return deleted_count, freed_space



def display_cleanup_section(all_results):
    """Display old reports cleanup section"""
    with st.expander("Cleanup old reports", expanded=False):
        # Load current configuration
        config = load_cleanup_config()
        retention_days = config.get('retention_days', DEFAULT_RETENTION_DAYS)

        # Settings
        st.markdown("#### Retention period settings")

        # Show setting source
        source = config.get('source', 'default')
        if source == 'env':
            st.info(f"Setting configured via environment variable `{ENV_RETENTION_DAYS}={retention_days}` days")
            st.number_input(
                "Keep reports (days)",
                min_value=1,
                max_value=365,
                value=retention_days,
                disabled=True,
                help="Value set via environment variable"
            )
        else:
            retention_days_input = st.number_input(
                "Keep reports (days)",
                min_value=1,
                max_value=365,
                value=retention_days,
                help="Reports older than this period are deleted automatically"
            )

            # Save settings
            if st.button("Save settings"):
                config['retention_days'] = retention_days_input
                save_cleanup_config(config)
                st.success("Settings saved")
                st.rerun()

        # Manual cleanup
        if st.button("Clean up old reports now"):
            with st.spinner("Cleaning..."):
                deleted_count, freed_space = cleanup_old_reports(retention_days)
                if deleted_count > 0:
                    freed_mb = freed_space / (1024 * 1024)
                    st.success(f"Deleted {deleted_count} old reports, freed {freed_mb:.1f} MB")
                else:
                    st.info("No old reports found for deletion")

        st.info("Old reports are automatically deleted when opening this page")


def get_reports_list(limit=500, force_refresh=False, _version="v2"):
    """Get list of reports without caching"""
    return list_results(limit=limit, order_by='timestamp DESC')

def display_reports_overview():
    """Display reports page overview"""
    st.markdown("View and manage reports for all clusters")

    # Caching disabled

    # Removed refresh button for minimalist design

    clusters = list_clusters()
    all_results = get_reports_list(limit=500)  # Use cached function

    if not all_results:
        st.info("No available reports. Run inspection to create reports.")
        if st.button("Run inspection", type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")
        return

    # Old reports cleanup section
    display_cleanup_section(all_results)

    st.divider()

    # Information about number of reports
    st.info(f"Found {len(all_results)} reports")

    # Minimalist design - removed unnecessary warnings

    # Simple filters
    col1, col2 = st.columns(2)
    with col1:
        selected_cluster = st.selectbox("Cluster", ["All"] + clusters)
    with col2:
        date_filter = st.selectbox("Period", ["All", "Today", "Last 7 days", "Last 30 days"])

    filtered_results = all_results
    if selected_cluster != "All":
        filtered_results = [r for r in filtered_results if r["cluster_name"] == selected_cluster]

    now = datetime.now()
    if date_filter != "All":
        if date_filter == "Today":
            filtered_results = [r for r in filtered_results if
                                datetime.fromisoformat(r['timestamp']).date() == now.date()]
        elif date_filter == "Last 7 days":
            week_ago = now - timedelta(days=7)
            filtered_results = [r for r in filtered_results if
                                datetime.fromisoformat(r['timestamp']) >= week_ago]
        elif date_filter == "Last 30 days":
            month_ago = now - timedelta(days=30)
            filtered_results = [r for r in filtered_results if
                                datetime.fromisoformat(r['timestamp']) >= month_ago]

    if filtered_results:
        display_statistics_overview(filtered_results)
        display_reports_table(filtered_results)
    else:
        st.info("No reports found for selected criteria")


def display_statistics_overview(filtered_results):
    """Show statistics overview"""
    st.markdown("### Statistics")

    total_reports = len(filtered_results)
    total_critical = sum(r['critical'] for r in filtered_results)
    total_warnings = sum(r['warning'] for r in filtered_results)
    total_info = sum(r.get('info', 0) for r in filtered_results)  # Add info errors count
    total_passed = sum(r['passed'] for r in filtered_results)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Reports", total_reports)
    with col2:
        st.metric("Critical", total_critical)
    with col3:
        st.metric("Warnings", total_warnings)
    with col4:
        st.metric("Other", total_info)
    with col5:
        st.metric("Passed", total_passed)
    with col6:
        latest_report = max(filtered_results, key=lambda x: x['timestamp'])
        latest_time = datetime.fromisoformat(latest_report['timestamp']).strftime('%m-%d %H:%M')
        st.metric("Latest", latest_time)


def display_reports_table(filtered_results):
    """Show list of reports with selection option"""
    st.markdown("### Reports list")

    if not filtered_results:
        st.info("No available reports")
        return

    sorted_results = sorted(filtered_results,
                           key=lambda x: (-x['critical'], -x['warning'], -x.get('info', 0), x['timestamp']),
                           reverse=True)

    df_data = []
    for result in sorted_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        critical_count = result['critical']
        warning_count = result['warning']
        info_count = result.get('info', 0)  # Add info errors
        total_exceptions = critical_count + warning_count + info_count

        df_data.append({
            "ID": result['result_id'],
            "Cluster": result['cluster_name'],
            "Time": timestamp.strftime('%m-%d %H:%M'),
            "Type": "Immediate" if result['inspection_type'] == 'immediate' else "Scheduled",
            "Status": "Error" if total_exceptions > 0 else "OK",
            "Critical": critical_count,
            "Warnings": warning_count,
            "Other": info_count,
            "Passed": result['passed']
        })

    df = pd.DataFrame(df_data)

    event = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "ID": st.column_config.TextColumn("ID"),
            "Cluster": st.column_config.TextColumn("Cluster"),
            "Time": st.column_config.TextColumn("Time"),
            "Type": st.column_config.TextColumn("Type"),
            "Status": st.column_config.TextColumn("Status"),
            "Critical": st.column_config.NumberColumn("Critical"),
            "Warnings": st.column_config.NumberColumn("Warnings"),
            "Other": st.column_config.NumberColumn("Other"),
            "Passed": st.column_config.NumberColumn("Passed")
        }
    )

    if len(event.selection.rows) > 0:
        selected_row = event.selection.rows[0]
        selected_result = sorted_results[selected_row]
        st.session_state.selected_report_id = selected_result['result_id']
        st.session_state.view_mode = "operations"
        st.rerun()


def delete_report(report_id):
    """Delete report file"""
    import os
    from pathlib import Path

    results_dir = Path(__file__).parent.parent / "data" / "results"
    for file_path in results_dir.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('result_id') == report_id:
                os.remove(file_path)
                return True
        except:
            continue
    return False


from utils.inspection_result import export_report


def display_report_operations(report_id):
    """Display report operations page"""
    if st.button("Back to reports list"):
        st.session_state.view_mode = "list"
        st.rerun()

    report_data = load_result(report_id)
    if not report_data:
        st.error("Failed to load report data")
        return

    st.markdown(f"### Report operations center")

    col1, col2 = st.columns([3, 1])
    with col1:
        timestamp = datetime.fromisoformat(report_data['timestamp'])
        st.markdown(f"""
        **Report ID:** `{report_id}`
        **Cluster:** {report_data['cluster_name']}
        **Inspection time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        **Type:** {'Immediate inspection' if report_data['inspection_type'] == 'immediate' else 'Scheduled inspection'}
        """)

    with col2:
        if 'inspection_results' in report_data:
            all_items = []
            for inspector_type, inspector_result in report_data['inspection_results'].items():
                items = inspector_result.get('items', [])
                all_items.extend(items)
        else:
            all_items = report_data.get('items', [])

        exception_critical_count = 0
        exception_warning_count = 0
        passed_count = 0

        for item in all_items:
            if isinstance(item, dict):
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'unknown')
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
                severity = getattr(item, 'severity', 'unknown')
            else:
                status = 'unknown'
                severity = 'unknown'

            if status == 'passed':
                passed_count += 1
            elif status == 'exception':
                if severity == 'critical':
                    exception_critical_count += 1
                elif severity == 'warning':
                    exception_warning_count += 1

        if exception_critical_count > 0 or exception_warning_count > 0:
            if exception_critical_count > 0:
                st.error(f"Critical errors: {exception_critical_count}")
            if exception_warning_count > 0:
                st.warning(f"Warnings: {exception_warning_count}")
        else:
            st.success("All checks passed")
        st.info(f"Total: {len(all_items)}")

    st.divider()

    st.markdown("### Operations")

    col1, col2, col3 = st.columns(3)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("View details", type="primary", width='stretch'):
            st.session_state.view_mode = "detail"
            st.rerun()

    with col2:
        if st.button("Export JSON", width='stretch'):
            export_and_download(report_id, "json", "JSON")

    with col3:
        if st.button("Export Excel", width='stretch'):
            export_and_download(report_id, "excel", "Excel")

    with col4:
        if st.button("Export PDF", width='stretch'):
            success, message = export_report(report_id, "pdf")
            if success:
                st.success("PDF report created successfully!")
                try:
                    with open(message, "rb") as f:
                        pdf_data = f.read()
                    st.download_button(
                        label="Download PDF report",
                        data=pdf_data,
                        file_name=f"{report_id}.pdf",
                        mime="application/pdf",
                        type="secondary",
                        width='stretch'
                    )
                    # Remove file from exports folder after download
                    os.remove(message)
                except Exception as e:
                    st.error(f"Error reading PDF file: {str(e)}")
            else:
                if "reportlab" in message:
                    st.error(f"{message}")
                    st.info("Install reportlab for PDF export: `pip install reportlab`")
                else:
                    st.error(f"{message}")

    st.markdown("#### Deletion")
    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Deletion is irreversible, be careful")

    with col2:
        confirm_key = f"confirm_delete_{report_id}"
        if st.session_state.get(confirm_key, False):
            if st.button("Confirm deletion", type="primary", width='stretch'):
                try:
                    delete_report(report_id)
                    st.success(f"Report {report_id} deleted")
                    if confirm_key in st.session_state:
                        del st.session_state[confirm_key]
                    st.session_state.view_mode = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during deletion: {str(e)}")
        else:
            if st.button("Delete", width='stretch'):
                st.session_state[confirm_key] = True
                st.rerun()

    if st.session_state.get(confirm_key, False):
        st.warning("Click confirmation to delete the report")


def display_report_detail(report_id):
    """Display report details"""
    if st.button("Back to operations"):
        st.session_state.view_mode = "operations"
        st.rerun()

    report_data = load_result(report_id)
    if not report_data:
        st.error("Failed to load report data")
        return

    st.markdown(f"## Report details")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        **Report ID:** `{report_id}`
        **Cluster:** {report_data['cluster_name']}
        **Time:** {datetime.fromisoformat(report_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
        **Type:** {'Immediate inspection' if report_data['inspection_type'] == 'immediate' else 'Scheduled inspection'}
        """)

    with col2:
        if 'inspection_results' in report_data:
            all_items = []
            for inspector_type, inspector_result in report_data['inspection_results'].items():
                items = inspector_result.get('items', [])
                all_items.extend(items)
        else:
            all_items = report_data.get('items', [])

        exception_count = 0
        passed_count = 0

        for item in all_items:
            if isinstance(item, dict):
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'unknown')
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
                severity = getattr(item, 'severity', 'unknown')
            else:
                status = 'unknown'
                severity = 'unknown'

            if status == 'passed':
                passed_count += 1
            elif status == 'exception' and severity == 'critical':
                exception_count += 1

        if exception_count > 0:
            st.error(f"Found {exception_count} critical errors")
        else:
            st.success(f"All passed ({passed_count} items)")

    st.divider()

    display_inspection_items(all_items, report_id=report_id)


def display_report_preview(report_id):
    """Show quick report preview - version with simplified status system"""
    if st.button("Back"):
        st.session_state.view_mode = "list"
        st.rerun()

    st.markdown(f"## Report preview - {report_id}")

    report_data = load_result(report_id)
    if not report_data:
        st.error("Failed to load report data")
        return

    if 'inspection_results' in report_data:
        all_items = []
        for inspector_type, inspector_result in report_data['inspection_results'].items():
            items = inspector_result.get('items', [])
            all_items.extend(items)
    else:
        all_items = report_data.get('items', [])

    exception_critical = []
    exception_warning = []
    exception_other = []
    passed_items = []

    for item in all_items:
        if isinstance(item, dict):
            status = item.get('status', 'unknown')
            severity = item.get('severity', 'unknown')
        elif hasattr(item, 'status'):
            status = getattr(item, 'status', 'unknown')
            severity = getattr(item, 'severity', 'unknown')
        else:
            continue

        if status == 'passed':
            passed_items.append(item)
        elif status == 'exception':
            if severity == 'critical':
                exception_critical.append(item)
            elif severity == 'warning':
                exception_warning.append(item)
            else:
                exception_other.append(item)

    col1, col2 = st.columns(2)
    with col1:
        if exception_critical:
            st.error(f"Critical errors: {len(exception_critical)}")
        if exception_warning:
            st.warning(f"Warnings: {len(exception_warning)}")
        if exception_other:
            st.info(f"Other errors: {len(exception_other)}")

    with col2:
        st.success(f"Passed: {len(passed_items)}")
        st.info(f"Total: {len(all_items)}")

    if exception_critical:
        st.markdown("### Critical errors")
        for item in exception_critical[:5]:
            st.error(f"**{item.get('name', 'Unknown item')}:** {item.get('description', '')}")
        if len(exception_critical) > 5:
            st.info(f"And {len(exception_critical) - 5} more critical errors, see full report for details")
    elif exception_warning:
        st.markdown("### Warnings")
        for item in exception_warning[:3]:
            st.warning(f"**{item.get('name', 'Unknown item')}:** {item.get('description', '')}")
        if len(exception_warning) > 3:
            st.info(f"And {len(exception_warning) - 3} more warnings, see full report for details")

    if st.button("View full report", type="primary"):
        st.session_state.view_mode = "detail"
        st.rerun()

def display_inspection_items(items, report_id=None):
    """Display inspection details - version with simplified status system"""
    # Classification by new status: passed vs errors (with severity separation)
    passed_items = [item for item in items if item.get('status') == 'passed']
    exception_critical = [item for item in items
                         if item.get('status') == 'exception' and item.get('severity') == 'critical']
    exception_warning = [item for item in items
                        if item.get('status') == 'exception' and item.get('severity') == 'warning']
    exception_info = [item for item in items
                     if item.get('status') == 'exception' and item.get('severity') in ['info', 'error'] or
                     (item.get('status') == 'exception' and item.get('severity') not in ['critical', 'warning'])]

    # Create tabs
    tab_names = []
    tab_data = []

    # Prefer to display critical errors
    if exception_critical:
        tab_names.append(f"Critical errors ({len(exception_critical)})")
        tab_data.append(exception_critical)

    if exception_warning:
        tab_names.append(f"Warnings ({len(exception_warning)})")
        tab_data.append(exception_warning)

    if exception_info:
        tab_names.append(f"Other errors ({len(exception_info)})")
        tab_data.append(exception_info)

    # Display passed checks at the end
    if passed_items:
        tab_names.append(f"Passed ({len(passed_items)})")
        tab_data.append(passed_items)

    if tab_names:
        tabs = st.tabs(tab_names)
        for i, (tab, data) in enumerate(zip(tabs, tab_data)):
            with tab:
                display_items_list(data, tab_names[i].startswith("Passed"), report_id=report_id, tab_name=tab_names[i])


def display_items_list(items, is_passed=False, report_id=None, tab_name=None):
    """Display list of checks - version with simplified status system"""
    if not items:
        st.info("No items in this category yet")
        return

    # For passed items, collapsed display by default
    for idx, item in enumerate(items):
        title = f"{item.get('name', 'Unknown check item')}"
        expanded = not is_passed and item.get('severity') == 'critical'
        with st.expander(title, expanded=expanded):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Description:** {item.get('description', 'none')}")
                details = item.get('details', '')
                if details:
                    if 'violations' in item and isinstance(item['violations'], list):
                        st.markdown("**Resource violations:**")
                        import hashlib
                        base = f"{item.get('name','')}_{item.get('description','')[:50]}_{report_id or ''}_{tab_name or ''}_{idx}"
                        item_key = hashlib.md5(base.encode()).hexdigest()[:12]
                        safe_display_opa_violations_table(item['violations'], show_expander=False, table_key=item_key)
                    else:
                        st.markdown("**Details:**")
                        st.text(details)
            with col2:
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'info')
                if status == 'exception':
                    if severity == 'critical':
                        st.error("Critical error")
                    elif severity == 'warning':
                        st.warning("Regular error")
                    else:
                        st.info("Other error")
                elif status == 'passed':
                    st.success("Passed")
                else:
                    st.info("Unknown status")
            solution = item.get('solution', '')
            if solution:
                st.markdown("**Solution recommendations:**")
                st.info(solution)


def display_export_page(report_id):
    """Show export page - optimized version"""
    if st.button("Back"):
        st.session_state.view_mode = "list"
        st.rerun()

    st.markdown(f"### Report export - {report_id}")

    # Quick export
    st.markdown("#### Quick export")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Export to JSON", width='stretch'):
            export_and_download(report_id, "json", "JSON")

    with col2:
        if st.button("Export to Excel", width='stretch'):
            export_and_download(report_id, "excel", "Excel")

    st.divider()

    # Custom export options
    st.markdown("#### Export settings")
    col1, col2 = st.columns([2, 1])

    with col1:
        export_format = st.selectbox(
            "Select export format",
            ["JSON", "Excel"],
            help="Select format for report export"
        )

        include_passed = st.checkbox("Include passed checks", value=False,
                                    help="By default only errors are exported, check to include all checks")

        include_details = st.checkbox("Include details", value=True,
                                     help="Include detailed information about errors and recommendations")

    with col2:
        st.markdown("**Export content preview**")
        report_data = load_result(report_id)
        if report_data:
            total_items = 0
            exception_items = 0

            if 'inspection_results' in report_data:
                for inspector_type, inspector_result in report_data['inspection_results'].items():
                    items = inspector_result.get('items', [])
                    total_items += len(items)
                    exception_items += len([item for item in items if item.get('status') != 'passed'])

            st.metric("Total checks", total_items)
            st.metric("Errors", exception_items)

            if include_passed:
                st.info(f"{total_items} records will be exported")
            else:
                st.info(f"{exception_items} errors will be exported")

    if st.button("Start export", type="primary"):
        export_and_download(report_id, export_format.lower(), export_format,
                            include_passed, include_details)


def export_and_download(report_id, format_type, format_name, include_passed=False, include_details=True):
    """Perform export and provide file for download"""
    try:
        from utils.inspection_result import export_report

        success, file_path = export_report(report_id, format_type)

        if success:
            st.success(f"Export to {format_name} completed successfully!")

            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                mime_types = {
                    "json": "application/json",
                    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
                st.download_button(
                    label=f"Download {format_name} file",
                    data=file_data,
                    file_name=os.path.basename(file_path),
                    mime=mime_types.get(format_type, "application/octet-stream"),
                    type="secondary",
                    width='stretch'
                )
                # Remove file from exports folder after download
                os.remove(file_path)
                file_size = len(file_data) / 1024
                st.caption(f"File size: {file_size:.1f} KB")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        else:
            st.error(f"Export failed: {file_path}")
    except Exception as e:
        st.error(f"Export error: {str(e)}")


def main():
    """Main function"""
    initialize_page(
        title="Inspection reports",
        page_title="Inspection reports",
        page_subtitle="Cluster status overview"
    )

    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "list"
    if 'selected_report_id' not in st.session_state:
        st.session_state.selected_report_id = None

    if st.session_state.view_mode == "list":
        display_reports_overview()
    elif st.session_state.view_mode == "operations":
        if st.session_state.selected_report_id:
            display_report_operations(st.session_state.selected_report_id)
        else:
            st.error("Report not selected")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "detail":
        if st.session_state.selected_report_id:
            display_report_detail(st.session_state.selected_report_id)
        else:
            st.error("Report not selected")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "preview":
        if st.session_state.selected_report_id:
            display_report_preview(st.session_state.selected_report_id)
        else:
            st.error("Report not selected")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "export":
        if st.session_state.selected_report_id:
            display_export_page(st.session_state.selected_report_id)
        else:
            st.session_state.view_mode = "list"
            st.rerun()


if __name__ == "__main__":
    main()
