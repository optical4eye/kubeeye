#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Result display component
"""
import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Any, Optional

def display_status(status):
    """Display status color label"""
    status_colors = {
        'passed': 'green',
        'failed': 'red',
        'warning': 'yellow',
        'error': 'red',
        'skipped': 'white'
    }
    return status_colors.get(status, 'unknown')

def format_status_badge(status):
    """Format status badge"""
    status_map = {
        'passed': 'Passed',
        'failed': 'Failed',
        'warning': 'Warning',
        'error': 'Error',
        'skipped': 'Skipped'
    }
    return status_map.get(status, f'{status}')

def parse_opa_violations_to_table(violations_text):
    """Parse OPA violations text into table format"""
    if not violations_text or violations_text == "no violations":
        return []

    violations = []
    lines = violations_text.split('\n')
    current_violation = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith('name:'):
            if current_violation:
                violations.append(current_violation)
            current_violation = {'name': line.split(':', 1)[1].strip()}
        elif line.lower().startswith('kind:'):
            current_violation['kind'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('namespace:'):
            current_violation['namespace'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('message:'):
            current_violation['message'] = line.split(':', 1)[1].strip()
    if current_violation:
        violations.append(current_violation)
    return violations

def get_items_safely(result):
    """Safely get result.items, considering methods and properties"""
    if not result:
        return []
    if hasattr(result, 'items'):
        items_attr = getattr(result, 'items')
        if callable(items_attr):
            try:
                items = items_attr()
            except:
                items = []
        else:
            items = items_attr if isinstance(items_attr, list) else []
    elif isinstance(result, dict) and 'items' in result:
        items = result['items'] if isinstance(result['items'], list) else []
    else:
        items = []
    return items

def count_status(items):
    """Count by statuses"""
    status_counts = {
        'passed': 0,
        'failed': 0,
        'warning': 0,
        'error': 0,
        'skipped': 0,
    }
    for item in items:
        if isinstance(item, dict):
            status = item.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
    return status_counts

def display_opa_violations_table(violations_data: List[Dict], show_expander: bool = True, table_key: str = None):
    """Display OPA violations table - optimized version"""
    if not violations_data:
        st.info("No violations")
        return
    df = pd.DataFrame(violations_data)
    column_mapping = {
        'kind': 'Resource Type',
        'name': 'Resource Name',
        'namespace': 'Namespace',
        'message': 'Violation Details'
    }
    df = df.rename(columns=column_mapping)
    st.markdown("**Violations List:**")
    if len(violations_data) <= 10:
        st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            column_config={
                "Resource Type": st.column_config.TextColumn("Resource Type", help="Kubernetes resource type"),
                "Resource Name": st.column_config.TextColumn("Resource Name", help="Resource name"),
                "Namespace": st.column_config.TextColumn("Namespace", help="Kubernetes namespace"),
                "Violation Details": st.column_config.TextColumn("Violation Details", help="Violation description")
            },
            height=min(400, len(violations_data) * 50 + 100)
        )
    else:
        st.info(f"Found {len(violations_data)} violations, showing paginated")
        page_size = 10
        total_pages = (len(violations_data) + page_size - 1) // page_size
        if total_pages > 1:
            if table_key:
                selectbox_key = f"violations_page_{table_key}"
            else:
                import hashlib
                violations_hash = hashlib.md5(str(violations_data).encode()).hexdigest()[:8]
                selectbox_key = f"violations_page_{violations_hash}"
            page_state_key = f"{selectbox_key}_current_page"
            if page_state_key not in st.session_state:
                st.session_state[page_state_key] = 1
            page = st.selectbox(
                "Select page",
                range(1, total_pages + 1),
                format_func=lambda x: f"Page {x} of {total_pages}",
                key=selectbox_key,
                index=st.session_state[page_state_key] - 1
            )
            st.session_state[page_state_key] = page
            page -= 1
        else:
            page = 0
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(violations_data))
        page_df = df.iloc[start_idx:end_idx]
        st.dataframe(
            page_df,
            width='stretch',
            hide_index=True,
            column_config={
                "Resource Type": st.column_config.TextColumn("Resource Type"),
                "Resource Name": st.column_config.TextColumn("Resource Name"),
                "Namespace": st.column_config.TextColumn("Namespace"),
                "Violation Details": st.column_config.TextColumn("Violation Details"),
            },
            height=400
        )
        st.caption(f"Showing records {start_idx + 1} to {end_idx} of {len(violations_data)}")

    if show_expander and len(violations_data) > 0:
        with st.expander("View detailed list", expanded=False):
            for i, violation in enumerate(violations_data, 1):
                st.markdown(f"**{i}. {violation.get('Resource Type', violation.get('kind', 'Unknown'))}/{violation.get('Resource Name', violation.get('name', 'unnamed'))}**")
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**Namespace:** {violation.get('Namespace', violation.get('namespace', '-'))}")
                with col2:
                    message = violation.get('Violation Details', violation.get('message', 'No details'))
                    st.markdown(f"**Violation Details:** {message}")
                if i < len(violations_data):
                    st.divider()

def display_summary_metrics(all_results):
    """Display summary information by results"""
    if not all_results:
        return
    total_items = sum(len(get_items_safely(result)) for result in all_results.values())
    status_counts = {
        'passed': 0, 'failed': 0, 'warning': 0, 'error': 0, 'skipped': 0,
    }
    for result in all_results.values():
        result_counts = count_status(get_items_safely(result))
        for status, count in result_counts.items():
            status_counts[status] += count
    st.write(f"Total checked **{total_items}** items")
    status_col1, status_col2, status_col3, status_col4, status_col5 = st.columns(5)
    with status_col1: st.metric("Passed", status_counts['passed'])
    with status_col2: st.metric("Failed", status_counts['failed'])
    with status_col3: st.metric("Warnings", status_counts['warning'])
    with status_col4: st.metric("Errors", status_counts['error'])
    with status_col5: st.metric("Skipped", status_counts['skipped'])

def display_inspection_results(inspector_type: str, result, show_summary: bool = True):
    """
    Display inspection results — simplified status system

    Args:
        inspector_type: inspector type
        result: inspection result
        show_summary: whether to display summary information
    """
    if not result:
        st.info(f"Inspection result {inspector_type} is empty")
        return
    items = get_items_safely(result)
    if not items:
        st.info(f"No inspection items {inspector_type}")
        return
    passed_items = [item for item in items if item.get('status') == 'passed']
    failed_items = [item for item in items if item.get('status') == 'failed']
    warning_items = [item for item in items if item.get('status') == 'warning']
    error_items = [item for item in items if item.get('status') == 'error']
    if show_summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Passed", len(passed_items))
        with col2: st.metric("Failed", len(failed_items))
        with col3: st.metric("Warnings", len(warning_items))
        with col4: st.metric("Errors", len(error_items))
    if failed_items:
        st.markdown("#### Compliance Issues")
        for item in failed_items:
            with st.expander(f"{item.get('name', 'No name')} - {item.get('description', '')}", expanded=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Check:** {item.get('name', 'Unknown')}")
                    st.markdown(f"**Description:** {item.get('description', 'No description')}")
                with col2:
                    severity = item.get('severity', 'unknown')
                    if severity == 'critical':
                        st.error(f"Critical level: {severity}")
                    elif severity == 'warning':
                        st.warning(f"Warning level: {severity}")
                    else:
                        st.info(f"Level: {severity}")
                st.divider()
                details_content = item.get('details', '')
                if details_content and details_content != "no violations":
                    violations_data = []
                    if 'violations' in item and isinstance(item['violations'], list):
                        violations_data = item['violations']
                    else:
                        violations_data = parse_opa_violations_to_table(details_content)
                    if violations_data:
                        violations_container = st.container()
                        with violations_container:
                            import hashlib
                            item_key = hashlib.md5(f"{item.get('name', '')}_error_{len(violations_data)}".encode()).hexdigest()[:8]
                            display_opa_violations_table(violations_data, show_expander=False, table_key=item_key)
                    else:
                        st.text_area("Details", details_content, height=150)
                if item.get('solution'):
                    st.divider()
                    st.markdown("**Solution:**")
                    st.info(item['solution'])
    if warning_items:
        st.markdown("#### Compliance Warnings")
        for item in warning_items:
            with st.expander(f"{item.get('name', 'No name')} - {item.get('description', '')}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Check:** {item.get('name', 'Unknown')}")
                    st.markdown(f"**Description:** {item.get('description', 'No description')}")
                with col2:
                    severity = item.get('severity', 'warning')
                    st.warning(f"Warning level: {severity}")
                st.divider()
                details_content = item.get('details', '')
                if details_content and details_content != "no violations":
                    violations_data = []
                    if 'violations' in item and isinstance(item['violations'], list):
                        violations_data = item['violations']
                    else:
                        violations_data = parse_opa_violations_to_table(details_content)
                    if violations_data:
                        violations_container = st.container()
                        with violations_container:
                            import hashlib
                            item_key = hashlib.md5(f"{item.get('name', '')}_warning_{len(violations_data)}".encode()).hexdigest()[:8]
                            display_opa_violations_table(violations_data, show_expander=False, table_key=item_key)
                    else:
                        st.text_area("Details", details_content, height=150)
                if item.get('solution'):
                    st.divider()
                    st.markdown("**Recommendations:**")
                    st.info(item['solution'])
    if error_items:
        st.markdown("#### System Errors")
        for item in error_items:
            with st.expander(f"{item.get('name', 'No name')} - {item.get('description', '')}"):
                st.error(f"Error information: {item.get('details', 'No details')}")
                if item.get('solution'):
                    st.markdown("**Solution:**")
                    st.info(item['solution'])

def display_result_summary(results):
    """Display results summary"""
    if not results:
        st.info("No inspection results")
        return
    total_passed = 0
    total_failed = 0
    total_warning = 0
    total_error = 0
    for result in results.values():
        items = get_items_safely(result)
        status_counts = count_status(items)
        total_passed += status_counts['passed']
        total_failed += status_counts['failed']
        total_warning += status_counts['warning']
        total_error += status_counts['error']
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Passed", total_passed)
    with col2:
        st.metric("Failed", total_failed)
    with col3:
        st.metric("Warnings", total_warning)
    with col4:
        st.metric("Errors", total_error)

def display_opa_results(result):
    """Display OPA inspection results"""
    return display_inspection_results("OPA", result)

def display_node_results(result):
    """Display node inspection results"""
    return display_inspection_results("Node inspection", result)

def display_prometheus_results(result):
    """Display Prometheus inspection results"""
    return display_inspection_results("Prometheus", result)
