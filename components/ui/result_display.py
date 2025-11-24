#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент отображения результатов проверки
"""
import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Any, Optional

def display_status(status):
    """Отобразить цветовую метку статуса"""
    status_colors = {
        'passed': '🟢',
        'failed': '🔴',
        'warning': '🟡',
        'error': '🔴',
        'skipped': '⚪'
    }
    return status_colors.get(status, '❓')

def format_status_badge(status):
    """Форматировать метку статуса"""
    status_map = {
        'passed': '✅ Пройдено',
        'failed': '❌ Провалено',
        'warning': '⚠️ Предупреждение',
        'error': '🔥 Ошибка',
        'skipped': '⏭️ Пропущено'
    }
    return status_map.get(status, f'❓ {status}')

def parse_opa_violations_to_table(violations_text):
    """Разобрать текст нарушений OPA в табличный формат"""
    if not violations_text or violations_text == "нет нарушений":
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
    """Безопасно получить result.items, учитывая методы и свойства"""
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
    """Подсчитать количество по статусам"""
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
    """Отобразить таблицу нарушений OPA - оптимизированная версия"""
    if not violations_data:
        st.info("Нет нарушений")
        return
    df = pd.DataFrame(violations_data)
    column_mapping = {
        'kind': 'Тип ресурса',
        'name': 'Имя ресурса',
        'namespace': 'Пространство имён',
        'message': 'Детали нарушения'
    }
    df = df.rename(columns=column_mapping)
    st.markdown("**Список нарушений:**")
    if len(violations_data) <= 10:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Тип ресурса": st.column_config.TextColumn("Тип ресурса", help="Тип ресурса Kubernetes"),
                "Имя ресурса": st.column_config.TextColumn("Имя ресурса", help="Имя ресурса"),
                "Пространство имён": st.column_config.TextColumn("Пространство имён", help="Kubernetes namespace"),
                "Детали нарушения": st.column_config.TextColumn("Детали нарушения", help="Описание нарушения")
            },
            height=min(400, len(violations_data) * 50 + 100)
        )
    else:
        st.info(f"Обнаружено {len(violations_data)} нарушений, показывается постранично")
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
                "Выберите страницу",
                range(1, total_pages + 1),
                format_func=lambda x: f"Страница {x} из {total_pages}",
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
            use_container_width=True,
            hide_index=True,
            column_config={
                "Тип ресурса": st.column_config.TextColumn("Тип ресурса"),
                "Имя ресурса": st.column_config.TextColumn("Имя ресурса"),
                "Пространство имён": st.column_config.TextColumn("Пространство имён"),
                "Детали нарушения": st.column_config.TextColumn("Детали нарушения"),
            },
            height=400
        )
        st.caption(f"Показаны записи с {start_idx + 1} по {end_idx} из {len(violations_data)}")

    if show_expander and len(violations_data) > 0:
        with st.expander("📋 Просмотр подробного списка", expanded=False):
            for i, violation in enumerate(violations_data, 1):
                st.markdown(f"**{i}. {violation.get('Тип ресурса', violation.get('kind', 'Unknown'))}/{violation.get('Имя ресурса', violation.get('name', 'unnamed'))}**")
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**Пространство имён:** {violation.get('Пространство имён', violation.get('namespace', '-'))}")
                with col2:
                    message = violation.get('Детали нарушения', violation.get('message', 'Нет подробностей'))
                    st.markdown(f"**Детали нарушения:** {message}")
                if i < len(violations_data):
                    st.divider()

def display_summary_metrics(all_results):
    """Отобразить сводную информацию по результатам"""
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
    st.write(f"Всего проверено **{total_items}** элементов")
    status_col1, status_col2, status_col3, status_col4, status_col5 = st.columns(5)
    with status_col1: st.metric("Пройдено", status_counts['passed'])
    with status_col2: st.metric("Провалено", status_counts['failed'])
    with status_col3: st.metric("Предупреждения", status_counts['warning'])
    with status_col4: st.metric("Ошибки", status_counts['error'])
    with status_col5: st.metric("Пропущено", status_counts['skipped'])

def display_inspection_results(inspector_type: str, result, show_summary: bool = True):
    """
    Отобразить результаты проверки — упрощённая система статусов

    Args:
        inspector_type: тип инспектора
        result: результат проверки
        show_summary: отображать ли сводную информацию
    """
    if not result:
        st.info(f"📝 Результат проверки {inspector_type} пуст")
        return
    items = get_items_safely(result)
    if not items:
        st.info(f"📝 Нет элементов проверки {inspector_type}")
        return
    passed_items = [item for item in items if item.get('status') == 'passed']
    failed_items = [item for item in items if item.get('status') == 'failed']
    warning_items = [item for item in items if item.get('status') == 'warning']
    error_items = [item for item in items if item.get('status') == 'error']
    if show_summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("✅ Пройдено", len(passed_items))
        with col2: st.metric("❌ Провалено", len(failed_items))
        with col3: st.metric("⚠️ Предупреждения", len(warning_items))
        with col4: st.metric("🔥 Ошибки", len(error_items))
    if failed_items:
        st.markdown("#### ❌ Проблемы соответствия")
        for item in failed_items:
            with st.expander(f"🔴 {item.get('name', 'Без имени')} - {item.get('description', '')}", expanded=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Проверка:** {item.get('name', 'Неизвестно')}")
                    st.markdown(f"**Описание:** {item.get('description', 'Без описания')}")
                with col2:
                    severity = item.get('severity', 'unknown')
                    if severity == 'critical':
                        st.error(f"🔴 Критический уровень: {severity}")
                    elif severity == 'warning':
                        st.warning(f"🟡 Уровень предупреждения: {severity}")
                    else:
                        st.info(f"ℹ️ Уровень: {severity}")
                st.divider()
                details_content = item.get('details', '')
                if details_content and details_content != "нет нарушений":
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
                        st.text_area("Детали", details_content, height=150)
                if item.get('solution'):
                    st.divider()
                    st.markdown("**💡 Решение:**")
                    st.info(item['solution'])
    if warning_items:
        st.markdown("#### ⚠️ Предупреждения соответствия")
        for item in warning_items:
            with st.expander(f"🟡 {item.get('name', 'Без имени')} - {item.get('description', '')}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Проверка:** {item.get('name', 'Неизвестно')}")
                    st.markdown(f"**Описание:** {item.get('description', 'Без описания')}")
                with col2:
                    severity = item.get('severity', 'warning')
                    st.warning(f"⚠️ Уровень предупреждения: {severity}")
                st.divider()
                details_content = item.get('details', '')
                if details_content and details_content != "нет нарушений":
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
                        st.text_area("Детали", details_content, height=150)
                if item.get('solution'):
                    st.divider()
                    st.markdown("**💡 Рекомендации:**")
                    st.info(item['solution'])
    if error_items:
        st.markdown("#### 🔥 Системные ошибки")
        for item in error_items:
            with st.expander(f"🔥 {item.get('name', 'Без имени')} - {item.get('description', '')}"):
                st.error(f"Информация об ошибке: {item.get('details', 'Нет подробностей')}")
                if item.get('solution'):
                    st.markdown("**💡 Решение:**")
                    st.info(item['solution'])

def display_result_summary(results):
    """Отобразить сводку результатов"""
    if not results:
        st.info("Нет результатов проверки")
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
        st.metric("✅ Пройдено", total_passed)
    with col2:
        st.metric("❌ Провалено", total_failed)
    with col3:
        st.metric("⚠️ Предупреждений", total_warning)
    with col4:
        st.metric("🔥 Ошибок", total_error)

def display_opa_results(result):
    """Отобразить результаты проверки OPA"""
    return display_inspection_results("OPA", result)

def display_node_results(result):
    """Отобразить результаты проверки узлов"""
    return display_inspection_results("Проверка узлов", result)

def display_prometheus_results(result):
    """Отобразить результаты проверки Prometheus"""
    return display_inspection_results("Prometheus", result)
