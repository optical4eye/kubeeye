#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduled scan component
"""
import streamlit as st
import pandas as pd
from utils.cluster_config import list_clusters, get_cluster
from utils.schedule_manager import (
    ScheduleTask, load_schedules, add_schedule, delete_schedule,
    run_inspection, restart_scheduler, start_scheduler, stop_scheduler
)

from components.ui import display_cluster_info
from utils.rule_manager import RuleManager

def render_scheduled_scan_tab():
    """Display scheduled scan tab"""
    st.subheader("Scheduled scan")

    if "scheduler_status" not in st.session_state:
        st.session_state.scheduler_status = True  # assume it's running

    scheduler_col1, scheduler_col2, scheduler_col3 = st.columns([1, 1, 2])
    with scheduler_col1:
        if st.session_state.scheduler_status:
            if st.button("Stop scheduler", key="stop_scheduler", type="primary"):
                if stop_scheduler():
                    st.session_state.scheduler_status = False
                    st.success("Scheduler stopped")
                    st.rerun()
                else:
                    st.error("Failed to stop scheduler")
        else:
            if st.button("Start scheduler", key="start_scheduler", type="primary"):
                if start_scheduler():
                    st.session_state.scheduler_status = True
                    st.success("Scheduler started")
                    st.rerun()
                else:
                    st.error("Failed to start scheduler")

    with scheduler_col2:
        if st.button("Restart tasks", key="restart_scheduler", type="primary"):
            if restart_scheduler():
                st.success("Tasks restarted")
                st.rerun()
            else:
                st.error("Failed to restart tasks")

    with scheduler_col3:
        scheduler_status_text = "Running" if st.session_state.scheduler_status else "Stopped"
        scheduler_status_color = "#00a971" if st.session_state.scheduler_status else "#ff4b4b"
        st.markdown(f"""
        <div style="padding: 8px; border-radius: 4px; background-color: #393E46; text-align: left;">
            <span>Scheduler status: </span>
            <span style="color: {scheduler_status_color}; font-weight: bold;">
                {scheduler_status_text}
            </span>
        </div>
        """, unsafe_allow_html=True)

    tasks = load_schedules()
    task_tab1, task_tab2 = st.tabs(["Task list", "Create new task"])

    with task_tab1:
        render_task_list_tab(tasks)

    with task_tab2:
        render_create_task_tab()

def render_task_list_tab(tasks):
    """Display task list"""
    if not tasks:
        st.info("No scheduled tasks created yet. Go to the 'Create new task' tab to add one.")
    else:
        task_data = []
        for task in tasks:
            if task.last_status == "success":
                status_text = "Completed"
            elif task.last_status == "running":
                status_text = "Running"
            elif task.last_status == "failed":
                status_text = "Failed"
            else:
                status_text = "Not executed"
            enabled_text = "Enabled" if task.enabled else "Disabled"
            next_run = task.get_next_run()
            next_run_text = next_run.strftime("%Y-%m-%d %H:%M") if next_run else "Not set"
            schedule_type = task.get_pretty_schedule()
            task_data.append({
                "Task name": task.name,
                "Cluster": task.cluster,
                "Schedule": schedule_type,
                "Status": status_text,
                "Enabled": enabled_text,
                "Last run": task.last_run.replace("T", " ").split(".")[0] if task.last_run else "Never started",
                "Next run": next_run_text,
                "ID": task.task_id
            })
        if task_data:
            task_df = pd.DataFrame(task_data)
            st.dataframe(task_df, width='stretch', hide_index=True)
            st.subheader("Task management")
            selected_task_id = st.selectbox(
                "Select task",
                [t["ID"] for t in task_data],
                format_func=lambda x: next((t["Task name"] for t in task_data if t["ID"] == x), x)
            )
            if selected_task_id:
                selected_task = next((t for t in tasks if t.task_id == selected_task_id), None)
                if selected_task:
                    with st.expander("Task details", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Name:** {selected_task.name}")
                            st.markdown(f"**Cluster:** {selected_task.cluster}")
                            st.markdown(f"**Description:** {selected_task.description}")
                        with col2:
                            st.markdown(f"**Schedule:** {selected_task.get_pretty_schedule()}")
                            st.markdown(f"**Status:** {selected_task.last_status}")
                            st.markdown(f"**Created:** {selected_task.created_at}")
                        st.markdown("#### Rule configuration")
                        rules = selected_task.rules
                        if rules:
                            for rule_type, rule_config in rules.items():
                                if rule_config.get('enabled', False):
                                    # Determine rule source for display
                                    use_gitops = RuleManager.should_use_gitops()
                                    source_text = "GitOps" if use_gitops else "local"
                                    st.write(f"**{rule_type.capitalize()}** rules: {len(rule_config.get('rules', []))} {source_text} rules")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Run now", key=f"run_{selected_task_id}", type="primary"):
                            success, message, results = run_inspection(selected_task_id, return_results=True)
                            if success:
                                st.success(f"Task {selected_task.name} completed successfully")
                                if results:
                                    total_items = sum(len(result.items) for result in results.values())
                                    st.info(f"Checked {total_items} items")
                                    st.info(f"{message}")
                                    if st.button("Go to detailed report", key="view_scheduled_report", type="primary"):
                                        st.switch_page("pages/3_inspect_report.py")
                                st.rerun()
                            else:
                                st.error(f"Task execution error: {message}")
                    with col2:
                        if selected_task.enabled:
                            if st.button("Disable task", key=f"disable_{selected_task_id}", type="primary"):
                                selected_task.enabled = False
                                if add_schedule(selected_task, update=True):
                                    st.success(f"Task {selected_task.name} disabled")
                                    restart_scheduler()
                                    st.rerun()
                                else:
                                    st.error("Failed to disable task")
                        else:
                            if st.button("Enable task", key=f"enable_{selected_task_id}", type="primary"):
                                selected_task.enabled = True
                                if add_schedule(selected_task, update=True):
                                    st.success(f"Task {selected_task.name} enabled")
                                    restart_scheduler()
                                    st.rerun()
                                else:
                                    st.error("Failed to enable task")
                    with col3:
                        if st.button("Delete task", key=f"delete_{selected_task_id}", type="primary"):
                            if delete_schedule(selected_task_id):
                                st.success(f"Task {selected_task.name} deleted")
                                restart_scheduler()
                                st.rerun()
                            else:
                                st.error("Failed to delete task")

def render_create_task_tab():
    """Display task creation tab"""
    import time

    st.subheader("Create new scheduled task")
    clusters = list_clusters()
    if not clusters:
        st.warning("No clusters configured yet. Please add a cluster on the 'Cluster info' page.")
        if st.button("Go to cluster info", key="goto_cluster_info_btn2", type="primary"):
            st.switch_page("pages/1_cluster_info.py")
        return

    schedule_types = ["One-time", "Periodic (Cron expression)"]
    if "schedule_type" not in st.session_state:
        st.session_state["schedule_type"] = schedule_types[0]
    st.session_state["schedule_type"] = st.selectbox(
        "Schedule type",
        schedule_types,
        index=schedule_types.index(st.session_state["schedule_type"]),
        key="schedule_type_selectbox"
    )
    task_type = st.session_state["schedule_type"]

    with st.form(key="new_task_form"):
        task_name = st.text_input("Task name", placeholder="Example: daily check")
        task_description = st.text_area("Task description", placeholder="Describe the task's purpose and scope")
        selected_cluster = st.selectbox("Select cluster", clusters)

        if selected_cluster:
            cluster_config, nodes, prometheus_config = display_cluster_info(selected_cluster)

        cron_expr = ""
        run_date = None
        run_time = None

        if task_type == "Periodic (Cron expression)":
            st.caption("Cron format: min hour day month day_of_week")
            cron_fields = [
                {"name": "Minutes", "key": "cron_min", "default": "0", "help": "0-59, * – every minute"},
                {"name": "Hours", "key": "cron_hour", "default": "8", "help": "0-23, * – every hour"},
                {"name": "Days", "key": "cron_dom", "default": "*", "help": "1-31, * – every day"},
                {"name": "Months", "key": "cron_month", "default": "*", "help": "1-12, * – every month"},
                {"name": "Days of week", "key": "cron_dow", "default": "*", "help": "0=sunday, 1=monday ... 6=saturday, * – every day of week"}
            ]
            cols = st.columns(len(cron_fields))
            cron_values = {}
            for i, field in enumerate(cron_fields):
                with cols[i]:
                    value = st.text_input(
                        field["name"],
                        value=st.session_state.get(field["key"], field["default"]),
                        key=field["key"],
                        help=field["help"]
                    )
                    cron_values[field["key"]] = value
            cron_expr = f"{cron_values['cron_min']} {cron_values['cron_hour']} {cron_values['cron_dom']} {cron_values['cron_month']} {cron_values['cron_dow']}"
            with st.expander("Cron examples"):
                st.markdown("""
                - `0 8 * * *` — daily at 8:00
                - `0 0 * * 0` — every Sunday at midnight
                - `0 18 * * 1-5` — weekdays at 18:00
                - `0 0 1 * *` — first day of every month at midnight
                - `*/15 * * * *` — every 15 minutes
                """)
        elif task_type == "One-time":
            col1, col2 = st.columns(2)
            with col1:
                run_date = st.date_input("Execution date", key="once_date")
            with col2:
                run_time = st.time_input("Execution time", key="once_time")

        cluster_config = get_cluster(selected_cluster)
        prometheus_config = cluster_config.get_prometheus_config() if cluster_config else None
        kubeconfig = cluster_config.get_kubeconfig() if cluster_config else None

        node_check = bool(cluster_config and cluster_config.get_nodes())
        prometheus_check = bool(prometheus_config and prometheus_config.get('enabled', False))
        opa_check = bool(kubeconfig)

        # Determine whether to use GitOps rules
        use_gitops = RuleManager.should_use_gitops()

        if use_gitops:
            st.info("Using GitOps rules")

        selected_node_rules, selected_prometheus_rules, selected_opa_rules = RuleManager.create_rule_selection_tabs(
            node_check, prometheus_check, opa_check, "_schedule", in_form=True, use_gitops=use_gitops
        )

        st.divider()
        st.divider()
        task_enabled = st.checkbox("Enable task immediately", value=True)
        submit_button = st.form_submit_button("Create task", type="primary")

        if submit_button:
            if not task_name:
                st.error("Enter task name")
            elif task_type == "Periodic (Cron expression)" and not cron_expr:
                st.error("Enter valid Cron expression")
            elif task_type == "One-time" and (not run_date or not run_time):
                st.error("Select date and time for execution")
            elif not (node_check or prometheus_check or opa_check):
                st.error("Select at least one inspection type")
            else:
                task_id = f"task_{int(time.time())}"
                task_type_map = {"One-time": "once", "Periodic (Cron expression)": "cron"}
                actual_task_type = task_type_map.get(task_type, "cron")
                run_datetime = None
                if task_type == "One-time":
                    run_datetime = f"{run_date} {run_time.strftime('%H:%M')}"
                    actual_cron_expr = ""
                else:
                    actual_cron_expr = cron_expr

                rules_config = {}
                if node_check:
                    rules_config["node"] = {"enabled": True, "rules": selected_node_rules}
                if prometheus_check:
                    rules_config["prometheus"] = {"enabled": True, "rules": selected_prometheus_rules}
                if opa_check:
                    rules_config["opa"] = {"enabled": True, "rules": selected_opa_rules}
                new_task = ScheduleTask(
                    task_id=task_id,
                    cluster=selected_cluster,
                    name=task_name,
                    description=task_description,
                    cron_expr=actual_cron_expr,
                    enabled=task_enabled,
                    rules=rules_config,
                    task_type=actual_task_type,
                    run_datetime=run_datetime
                )
                if add_schedule(new_task):
                    st.success("Scheduled scan task created successfully")
                    restart_scheduler()
                    st.rerun()
                else:
                    st.error("Task creation error")

        if submit_button and task_type == "Periodic (Cron expression)":
            st.info(f"Current Cron expression: `{cron_expr}`")
            cron_desc = get_cron_description(cron_values['cron_min'], cron_values['cron_hour'], cron_values['cron_dom'], cron_values['cron_month'], cron_values['cron_dow'])
            st.caption(f"Description: {cron_desc}")

def get_cron_description(minute, hour, dom, month, dow):
    """
    Convert cron expression to human-readable description in English.
    Supports basic cron formats.

    Args:
        minute: minute field (0-59)
        hour: hour field (0-23)
        dom: day of month (1-31)
        month: month (1-12)
        dow: day of week (0-6, 0 = sunday)
    Returns:
        str: cron expression description
    """
    mappings = {
        'minute': {'field': minute, 'wild': 'every minute', 'format': '{} minutes'},
        'hour': {'field': hour, 'wild': 'every hour', 'format': '{} hours'},
        'dom': {'field': dom, 'wild': 'every day', 'format': '{} of month'},
        'month': {'field': month, 'wild': 'every month', 'format': '{} month'},
        'dow': {'field': dow, 'wild': 'every week', 'format': 'day of week {}',
                'names': {'0': 'sunday', '1': 'monday', '2': 'tuesday', '3': 'wednesday', '4': 'thursday', '5': 'friday', '6': 'saturday'}}
    }
    parts = []
    for part_name, config in mappings.items():
        value = config['field']
        if value == '*':
            parts.append(config['wild'])
        elif part_name == 'dow' and value in config['names']:
            parts.append(config['format'].format(config['names'][value]))
        else:
            parts.append(config['format'].format(value))
    return ", ".join(parts)