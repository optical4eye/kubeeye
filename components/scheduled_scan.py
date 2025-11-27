#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент плановой проверки
"""
import streamlit as st
import pandas as pd
from utils.cluster_config import list_clusters, get_cluster
from utils.schedule_manager import (
    ScheduleTask, load_schedules, add_schedule, delete_schedule,
    run_inspection, restart_scheduler, start_scheduler, stop_scheduler
)

from components.ui import display_cluster_info, InspectionProgress
from utils.rule_manager import RuleManager

def render_scheduled_scan_tab():
    """Отобразить вкладку плановой проверки"""
    st.subheader("Плановая проверка")

    if "scheduler_status" not in st.session_state:
        st.session_state.scheduler_status = True  # предполагаем, что запущен

    scheduler_col1, scheduler_col2, scheduler_col3 = st.columns([1, 1, 2])
    with scheduler_col1:
        if st.session_state.scheduler_status:
            if st.button("Остановить планировщик", key="stop_scheduler"):
                if stop_scheduler():
                    st.session_state.scheduler_status = False
                    st.success("Планировщик остановлен")
                    st.rerun()
                else:
                    st.error("Не удалось остановить планировщик")
        else:
            if st.button("Запустить планировщик", key="start_scheduler"):
                if start_scheduler():
                    st.session_state.scheduler_status = True
                    st.success("Планировщик запущен")
                    st.rerun()
                else:
                    st.error("Не удалось запустить планировщик")

    with scheduler_col2:
        if st.button("Перезапустить задачи", key="restart_scheduler"):
            if restart_scheduler():
                st.success("Задачи перезапущены")
                st.rerun()
            else:
                st.error("Не удалось перезапустить задачи")

    with scheduler_col3:
        scheduler_status_text = "Запущен" if st.session_state.scheduler_status else "Остановлен"
        scheduler_status_color = "#00a971" if st.session_state.scheduler_status else "#ff4b4b"
        st.markdown(f"""
        <div style="padding: 8px; border-radius: 4px; background-color: #393E46; text-align: left;">
            <span>Статус планировщика: </span>
            <span style="color: {scheduler_status_color}; font-weight: bold;">
                {scheduler_status_text}
            </span>
        </div>
        """, unsafe_allow_html=True)

    tasks = load_schedules()
    task_tab1, task_tab2 = st.tabs(["Список задач", "Создать новую задачу"])

    with task_tab1:
        render_task_list_tab(tasks)

    with task_tab2:
        render_create_task_tab()

def render_task_list_tab(tasks):
    """Отобразить список задач"""
    if not tasks:
        st.info("Пока не создано ни одной плановой задачи. Перейдите на вкладку «Создать новую задачу» для добавления.")
    else:
        task_data = []
        for task in tasks:
            if task.last_status == "success":
                status_icon = "✅"
                status_text = "Выполнена"
            elif task.last_status == "running":
                status_icon = "⏳"
                status_text = "Выполняется"
            elif task.last_status == "failed":
                status_icon = "❌"
                status_text = "Сбой"
            else:
                status_icon = "⏸️"
                status_text = "Не выполнялась"
            enabled_text = "Включена" if task.enabled else "Отключена"
            next_run = task.get_next_run()
            next_run_text = next_run.strftime("%Y-%m-%d %H:%M") if next_run else "Не задано"
            schedule_type = task.get_pretty_schedule()
            task_data.append({
                "Название задачи": task.name,
                "Кластер": task.cluster,
                "Расписание": schedule_type,
                "Статус": f"{status_icon} {status_text}",
                "Включена": enabled_text,
                "Последний запуск": task.last_run.replace("T", " ").split(".")[0] if task.last_run else "Не запускалась",
                "Следующий запуск": next_run_text,
                "ID": task.task_id
            })
        if task_data:
            task_df = pd.DataFrame(task_data)
            st.dataframe(task_df, width='stretch', hide_index=True)
            st.subheader("Управление задачей")
            selected_task_id = st.selectbox(
                "Выберите задачу",
                [t["ID"] for t in task_data],
                format_func=lambda x: next((t["Название задачи"] for t in task_data if t["ID"] == x), x)
            )
            if selected_task_id:
                selected_task = next((t for t in tasks if t.task_id == selected_task_id), None)
                if selected_task:
                    with st.expander("Подробности задачи", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Название:** {selected_task.name}")
                            st.markdown(f"**Кластер:** {selected_task.cluster}")
                            st.markdown(f"**Описание:** {selected_task.description}")
                        with col2:
                            st.markdown(f"**Расписание:** {selected_task.get_pretty_schedule()}")
                            st.markdown(f"**Статус:** {selected_task.last_status}")
                            st.markdown(f"**Создана:** {selected_task.created_at}")
                        st.markdown("#### Конфигурация правил")
                        rules = selected_task.rules
                        if rules:
                            for rule_type, rule_config in rules.items():
                                if rule_config.get('enabled', False):
                                    # Определяем источник правил для отображения
                                    use_gitops = RuleManager.should_use_gitops()
                                    source_text = "GitOps" if use_gitops else "локальных"
                                    st.write(f"**{rule_type.capitalize()}** правила: {len(rule_config.get('rules', []))} {source_text} правил")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Выполнить сейчас", key=f"run_{selected_task_id}"):
                            from components.ui import execute_inspection_task
                            success, message, results = run_inspection(selected_task_id, return_results=True)
                            if success:
                                st.success(f"Задача {selected_task.name} успешно выполнена")
                                if results:
                                    total_items = sum(len(result.items) for result in results.values())
                                    st.info(f"✅ Проверено {total_items} элементов")
                                    st.info(f"📄 {message}")
                                    if st.button("📊 Перейти к подробному отчёту", key="view_scheduled_report"):
                                        st.switch_page("pages/3_inspect_report.py")
                                st.rerun()
                            else:
                                st.error(f"Ошибка выполнения задачи: {message}")
                    with col2:
                        if selected_task.enabled:
                            if st.button("Отключить задачу", key=f"disable_{selected_task_id}"):
                                selected_task.enabled = False
                                if add_schedule(selected_task, update=True):
                                    st.success(f"Задача {selected_task.name} отключена")
                                    restart_scheduler()
                                    st.rerun()
                                else:
                                    st.error("Не удалось отключить задачу")
                        else:
                            if st.button("Включить задачу", key=f"enable_{selected_task_id}"):
                                selected_task.enabled = True
                                if add_schedule(selected_task, update=True):
                                    st.success(f"Задача {selected_task.name} включена")
                                    restart_scheduler()
                                    st.rerun()
                                else:
                                    st.error("Не удалось включить задачу")
                    with col3:
                        if st.button("Удалить задачу", key=f"delete_{selected_task_id}", type="primary"):
                            if delete_schedule(selected_task_id):
                                st.success(f"Задача {selected_task.name} удалена")
                                restart_scheduler()
                                st.rerun()
                            else:
                                st.error("Не удалось удалить задачу")

def render_create_task_tab():
    """Отобразить вкладку создания новой задачи"""
    import time
    import yaml

    st.subheader("Создать новую плановую задачу")
    clusters = list_clusters()
    if not clusters:
        st.warning("Пока не настроены кластеры. Пожалуйста, добавьте кластер на странице «Информация о кластере».")
        if st.button("Перейти к информации о кластере", key="goto_cluster_info_btn2"):
            st.switch_page("pages/1_cluster_info.py")
        return

    schedule_types = ["Одноразовая", "Периодическая (Cron-выражение)"]
    if "schedule_type" not in st.session_state:
        st.session_state["schedule_type"] = schedule_types[0]
    st.session_state["schedule_type"] = st.selectbox(
        "Тип расписания",
        schedule_types,
        index=schedule_types.index(st.session_state["schedule_type"]),
        key="schedule_type_selectbox"
    )
    task_type = st.session_state["schedule_type"]

    with st.form(key="new_task_form"):
        task_name = st.text_input("Название задачи", placeholder="Например: ежедневная проверка")
        task_description = st.text_area("Описание задачи", placeholder="Опишите цель и охват задачи")
        selected_cluster = st.selectbox("Выберите кластер", clusters)

        if selected_cluster:
            cluster_config, nodes, prometheus_config = display_cluster_info(selected_cluster)

        cron_expr = ""
        run_date = None
        run_time = None

        if task_type == "Периодическая (Cron-выражение)":
            st.caption("Формат Cron: мин час день месяц день_недели")
            cron_fields = [
                {"name": "Минуты", "key": "cron_min", "default": "0", "help": "0-59, * – каждая минута"},
                {"name": "Часы", "key": "cron_hour", "default": "8", "help": "0-23, * – каждый час"},
                {"name": "Дни", "key": "cron_dom", "default": "*", "help": "1-31, * – каждый день"},
                {"name": "Месяцы", "key": "cron_month", "default": "*", "help": "1-12, * – каждый месяц"},
                {"name": "Дни недели", "key": "cron_dow", "default": "*", "help": "0=воскресенье, 1=понедельник ... 6=суббота, * – каждый день недели"}
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
            with st.expander("Примеры Cron"):
                st.markdown("""
                - `0 8 * * *` — ежедневно в 8:00
                - `0 0 * * 0` — каждое воскресенье в полночь
                - `0 18 * * 1-5` — в будние дни в 18:00
                - `0 0 1 * *` — первого числа каждого месяца в полночь
                - `*/15 * * * *` — каждые 15 минут
                """)
        elif task_type == "Одноразовая":
            col1, col2 = st.columns(2)
            with col1:
                run_date = st.date_input("Дата выполнения", key="once_date")
            with col2:
                run_time = st.time_input("Время выполнения", key="once_time")

        cluster_config = get_cluster(selected_cluster)
        prometheus_config = cluster_config.get_prometheus_config() if cluster_config else None
        kubeconfig = cluster_config.get_kubeconfig() if cluster_config else None

        node_check = bool(cluster_config and cluster_config.get_nodes())
        prometheus_check = bool(prometheus_config and prometheus_config.get('enabled', False))
        opa_check = bool(kubeconfig)

        # Определить, использовать ли правила GitOps
        use_gitops = RuleManager.should_use_gitops()

        if use_gitops:
            st.info("🔒 Используются правила GitOps")

        selected_node_rules, selected_prometheus_rules, selected_opa_rules = RuleManager.create_rule_selection_tabs(
            node_check, prometheus_check, opa_check, "_schedule", in_form=True, use_gitops=use_gitops
        )

        st.divider()
        st.divider()
        task_enabled = st.checkbox("Включить задачу сразу", value=True)
        submit_button = st.form_submit_button("Создать задачу")

        if submit_button:
            if not task_name:
                st.error("Введите имя задачи")
            elif task_type == "Периодическая (Cron-выражение)" and not cron_expr:
                st.error("Введите корректное Cron-выражение")
            elif task_type == "Одноразовая" and (not run_date or not run_time):
                st.error("Выберите дату и время запуска")
            elif not (node_check or prometheus_check or opa_check):
                st.error("Выберите хотя бы один тип проверки")
            else:
                task_id = f"task_{int(time.time())}"
                task_type_map = {"Одноразовая": "once", "Периодическая (Cron-выражение)": "cron"}
                actual_task_type = task_type_map.get(task_type, "cron")
                run_datetime = None
                if task_type == "Одноразовая":
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
                    st.success("Задача плановой проверки успешно создана")
                    restart_scheduler()
                    st.rerun()
                else:
                    st.error("Ошибка создания задачи")

        if submit_button and task_type == "Периодическая (Cron-выражение)":
            st.info(f"Текущее Cron-выражение: `{cron_expr}`")
            cron_desc = get_cron_description(cron_values['cron_min'], cron_values['cron_hour'], cron_values['cron_dom'], cron_values['cron_month'], cron_values['cron_dow'])
            st.caption(f"Описание: {cron_desc}")

def get_cron_description(minute, hour, dom, month, dow):
    """
    Преобразовать cron-выражение в человекочитаемое описание на русском.
    Поддерживает базовые форматы cron.

    Args:
        minute: поле минут (0-59)
        hour: поле часов (0-23)
        dom: день месяца (1-31)
        month: месяц (1-12)
        dow: день недели (0-6, 0 = воскресенье)
    Returns:
        str: описание cron-выражения
    """
    mappings = {
        'minute': {'field': minute, 'wild': 'каждую минуту', 'format': '{} минут'},
        'hour': {'field': hour, 'wild': 'каждый час', 'format': '{} часов'},
        'dom': {'field': dom, 'wild': 'каждый день', 'format': '{} числа месяца'},
        'month': {'field': month, 'wild': 'каждый месяц', 'format': '{} месяц'},
        'dow': {'field': dow, 'wild': 'каждую неделю', 'format': 'день недели {}',
                'names': {'0': 'воскресенье', '1': 'понедельник', '2': 'вторник', '3': 'среда', '4': 'четверг', '5': 'пятница', '6': 'суббота'}}
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
    return "，".join(parts)