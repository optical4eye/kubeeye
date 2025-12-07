#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye - Инструмент для инспекции кластера Kubernetes


Этот файл является точкой входа приложения, инициализирует интерфейс и отображает содержимое главной страницы.
"""


# Импорт стандартных библиотек
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Импорт сторонних библиотек
import streamlit as st
import pandas as pd
import plotly.express as px


# Настройка конфигурации страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="KubeEye - Инструмент для инспекции кластера Kubernetes",
    page_icon="🔍",
    layout="wide"
)


# Импорт модулей проекта
from utils.common import initialize_page
from utils.cluster_config import list_clusters, get_cluster, list_clusters_cached, get_cluster_status_counts_fast, get_cluster_quick_status
from utils.inspection_result import list_results, get_latest_result_by_cluster, load_result_minimal
from utils.rule_loader import load_rules
from utils.version import VERSION, APP_NAME, APP_DESCRIPTION, RELEASE_DATE
from utils.cert_checker import get_cluster_cert_status


# Инициализация страницы
initialize_page(
    title="KubeEye",
    icon="🔍",
    page_title="Обзор кластеров",
    page_subtitle="Мониторинг и инспекция Kubernetes кластеров"
)


# Оптимизированная загрузка dashboard с ограниченными данными
# Временно отключаем кэширование для диагностики
# @st.cache_data(ttl=300)  # Кэш на 5 минут
def get_dashboard_data() -> Dict:
    """Быстрая загрузка dashboard с ограниченными данными"""

    # Быстрая загрузка кластеров
    clusters = list_clusters()
    total_clusters = len(clusters)

    # Отладка внутри функции
    print(f"DEBUG: get_dashboard_data - clusters loaded: {len(clusters)}")
    if clusters:
        print(f"DEBUG: clusters: {clusters}")

    # Загрузка правил
    node_rules = load_rules('node')
    prometheus_rules = load_rules('prometheus')
    opa_rules = load_rules('opa')
    total_rules = len(node_rules) + len(prometheus_rules) + len(opa_rules)

    # Быстрый подсчёт статусов без загрузки всех результатов
    status_counts = get_cluster_status_counts_fast()

    # Загрузка только последних 20 результатов для таблицы
    recent_results = list_results(limit=20, order_by='timestamp DESC')

    # Статистика недавних сканирований (24 часа)
    now = datetime.now()
    cutoff_time = now.timestamp() - (24 * 3600)

    recent_scans = 0
    recent_issues = 0

    for result in recent_results:
        timestamp = datetime.fromisoformat(result['timestamp']).timestamp()
        if timestamp > cutoff_time:
            recent_scans += 1
            recent_issues += result.get('critical', 0) + result.get('warning', 0)

    # Время последней инспекции
    latest_scan_time = "Нет данных"
    if recent_results:
        latest_time = datetime.fromisoformat(recent_results[0]['timestamp'])
        latest_scan_time = latest_time.strftime("%m-%d %H:%M")

    # Создание упрощённых статусов кластеров (только необходимые поля)
    cluster_statuses = []
    for cluster_name in clusters:
        try:
            # Быстрая проверка статуса
            status = get_cluster_quick_status(cluster_name)
            latest_result = get_latest_result_by_cluster(cluster_name)

            cluster_status_dict = {
                'name': cluster_name,
                'status': status,
                'last_scan': latest_result['timestamp'] if latest_result else None,
                'critical_count': latest_result.get('critical', 0) if latest_result else 0,
                'warning_count': latest_result.get('warning', 0) if latest_result else 0,
                'passed_count': latest_result.get('passed', 0) if latest_result else 0,
                'node_count': 0,  # Загружается по требованию
                'cert_status': 'unknown',  # Загружается по требованию
                'cert_days_remaining': None
            }

            cluster_statuses.append(cluster_status_dict)
        except Exception:
            # В случае ошибки - минимальная информация
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


# Кэширование отключено для dashboard

# Очистка кэша при первой загрузке страницы (если есть параметр)
if st.query_params.get("clear_cache") == "true":
    get_dashboard_data.clear()
    st.query_params.clear()

# Восстанавливаем вызов get_dashboard_data() с обработкой ошибок
try:
    dashboard_data = get_dashboard_data()


except Exception as e:
    st.error(f"Ошибка загрузки данных dashboard: {str(e)}")
    # Загружаем минимальные данные для работы
    from utils.cluster_config import list_clusters
    clusters = list_clusters()
    dashboard_data = {
        'clusters': clusters,
        'cluster_statuses': [{'name': c, 'status': 'unknown', 'last_scan': None, 'critical_count': 0, 'warning_count': 0, 'passed_count': 0, 'node_count': 0, 'cert_status': 'unknown', 'cert_days_remaining': None} for c in clusters],
        'total_clusters': len(clusters),
        'recent_scans': 0,
        'recent_issues': 0,
        'latest_scan_time': "Ошибка загрузки",
        'total_rules': 0,
        'status_counts': {'healthy': 0, 'warning': 0, 'critical': 0, 'unknown': len(clusters) if clusters else 0},
        'recent_results': []
    }

# Вспомогательные функции для подсчёта ошибок
def count_errors_from_items(items):
    """Централизованная функция подсчёта ошибок по элементам"""
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
                # 'info' и другие severity не учитываются в основных счётчиках

    return {'critical': critical, 'warning': warning, 'passed': passed}

def count_errors_from_result(result_data):
    """Подсчёт ошибок из сохранённых данных результата"""
    # Для dashboard: все не-критические ошибки считаем как предупреждения
    critical = result_data.get('critical', 0)
    warning = result_data.get('warning', 0)
    passed = result_data.get('passed', 0)

    # В dashboard "предупреждения" включают все не-критические ошибки
    # (warning + info + error severity)
    # Но поскольку мы храним только critical/warning/passed,
    # предполагаем что все не-critical и не-warning - это другие типы ошибок
    # Пока оставляем как есть - только 'warning' severity
    return {
        'critical': critical,
        'warning': warning,
        'passed': passed
    }

# Минималистичные стили
st.markdown("""
<style>
/* Только необходимые стили для читаемости */
.stDataFrame { font-size: 14px; }
.stMetric { font-size: 16px; }

/* Responsive для мобильных */
@media (max-width: 768px) {
    .stDataFrame { font-size: 12px; }
    .stMetric { font-size: 14px; }
}
</style>
""", unsafe_allow_html=True)

# Toast уведомления для успешных операций
def show_toast(message, type="success"):
    toast_js = f"""
    <script>
    if (window.showToast) {{
        window.showToast("{message}", "{type}");
    }}
    </script>
    """
    st.markdown(toast_js, unsafe_allow_html=True)


# Развертывание данных из оптимизированной структуры
clusters = dashboard_data['clusters']
cluster_statuses = {cs['name']: cs for cs in dashboard_data['cluster_statuses']}

total_clusters = dashboard_data['total_clusters']
recent_scans = dashboard_data['recent_scans']
recent_issues = dashboard_data['recent_issues']
latest_scan_time = dashboard_data['latest_scan_time']
total_rules = dashboard_data['total_rules']
status_counts = dashboard_data['status_counts']
recent_results = dashboard_data['recent_results']

# Улучшенная диаграмма статусов кластеров (связанная с отчетами)
status_labels = {
    'healthy': 'Пройдено',      # Соответствует "✅ Пройдено" в отчетах
    'warning': 'Предупреждения', # Соответствует "🟡 Предупреждения" в отчетах
    'critical': 'Критические ошибки', # Соответствует "🔴 Критические ошибки" в отчетах
    'unknown': 'Неизвестно'
}
status_colors = {
    'healthy': '#10B981',    # Зеленый для пройденных (как в отчетах)
    'warning': '#F59E0B',    # Оранжевый для обычных ошибок (как в отчетах)
    'critical': '#EF4444',   # Красный для критических ошибок (как в отчетах)
    'unknown': '#6B7280'     # Серый для неизвестных
}

# Создаём кольцевую диаграмму с числами
fig_pie = px.pie(
    values=list(status_counts.values()),
    names=[f"{status_labels[k]} ({count})" for k, count in status_counts.items()],
    title="Распределение статусов кластеров",
    color=[status_labels[k] for k in status_counts.keys()],
    color_discrete_map=status_colors,
    hole=0.4  # Кольцевая диаграмма
)

# Улучшенные настройки отображения
fig_pie.update_traces(
    textposition='inside',
    textinfo='percent+value',
    hovertemplate='<b>%{label}</b><br>Количество: %{value}<br>Процент: %{percent}<extra></extra>',
    marker=dict(line=dict(color='white', width=2))
)

# Добавляем общее количество в центр
total_clusters = sum(status_counts.values())
fig_pie.add_annotation(
    text=f"<b>{total_clusters}</b><br>кластеров",
    x=0.5, y=0.5, showarrow=False,
    font=dict(size=16, color='#1f2937'),
    bgcolor='rgba(255,255,255,0.9)',
    bordercolor='#d1d5db',
    borderwidth=1,
    borderpad=4
)

# Улучшенная легенда
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


# Основные метрики
st.markdown("## Обзор")

# Подготовка данных для метрик
latest_scan_display = dashboard_data['latest_scan_time'] if dashboard_data['latest_scan_time'] != "Никогда не запускалась" else "Нет"

# Расчёт недавних проблем по типам (как в деталях отчётов)
now = datetime.now()
cutoff_time = now.timestamp() - (24 * 3600)  # 24 часа назад

recent_critical = 0
recent_warnings = 0
recent_info = 0
for result in recent_results:
    timestamp = datetime.fromisoformat(result['timestamp']).timestamp()
    if timestamp > cutoff_time:
        recent_critical += result.get('critical', 0)
        recent_warnings += result.get('warning', 0)
        recent_info += result.get('info', 0)  # Добавить подсчёт info ошибок

# Простые метрики в колонках (расширить до 7 колонок)
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    cluster_count = dashboard_data['total_clusters']
    st.metric("Кластеры", cluster_count)
with col2:
    st.metric("Инспекции", dashboard_data['recent_scans'])
with col3:
    st.metric("Критично", recent_critical)
with col4:
    st.metric("Предупреждения", recent_warnings)
with col5:
    st.metric("Прочее", recent_info)
with col6:
    st.metric("Последняя", latest_scan_display)
with col7:
    st.metric("Правила", dashboard_data['total_rules'])


# Отображение столбчатой диаграммы с боковой панелью статистики
if total_clusters > 0:
    col1, col2 = st.columns([2, 1])

    with col1:
        # Столбчатая диаграмма - отображаем все статусы с приоритетом на ошибки
        # Упорядочиваем: критические ошибки, предупреждения, пройдено, неизвестно
        status_order = ['critical', 'warning', 'healthy', 'unknown']
        ordered_labels = []
        ordered_values = []

        for status_key in status_order:
            if status_key in status_counts and status_counts[status_key] > 0:
                ordered_labels.append(status_labels[status_key])
                ordered_values.append(status_counts[status_key])

        # Создаем цветовую карту для меток (не для ключей)
        label_colors = {
            'Критические ошибки': '#EF4444',   # Красный для критических
            'Предупреждения': '#F59E0B',       # Оранжевый для предупреждений
            'Пройдено': '#10B981',             # Зеленый для пройденных
            'Неизвестно': '#6B7280'            # Серый для неизвестных
        }

        fig_bar = px.bar(
            x=ordered_labels,
            y=ordered_values,
            title="Распределение статусов кластеров",
            color=ordered_labels,  # Используем метки как категории цветов
            color_discrete_map=label_colors,  # Карта цветов по меткам
            text_auto=True
        )
        fig_bar.update_layout(
            xaxis_title="Статус кластеров",
            yaxis_title="Количество кластеров",
            showlegend=False
        )
        # Улучшенные hover для столбчатой диаграммы
        fig_bar.update_traces(
            hovertemplate='<b>%{x}</b><br>Количество: %{y}<extra></extra>'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("### 📊 Статистика")

        # Подсчёт общего количества ошибок из всех кластеров (используем централизованную функцию)
        total_critical_issues = 0
        total_warning_issues = 0
        total_passed_issues = 0

        for cs in dashboard_data['cluster_statuses']:
            # Используем централизованную функцию подсчёта
            counts = count_errors_from_result({
                'critical': cs.get('critical_count', 0),
                'warning': cs.get('warning_count', 0),
                'passed': cs.get('passed_count', 0)
            })
            total_critical_issues += counts['critical']
            total_warning_issues += counts['warning']
            total_passed_issues += counts['passed']

        # Ключевые метрики - общее количество ошибок (всегда отображаем)
        st.error(f"🔴 Критические ошибки: {total_critical_issues}")
        st.warning(f"🟡 Предупреждения: {total_warning_issues}")
        st.success(f"✅ Пройдено: {total_passed_issues}")

        # Кластеры по статусам с именами
        if dashboard_data['cluster_statuses']:
            st.markdown("**Кластеры по статусам:**")

            # Группируем кластеры по статусам
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

            # Отображаем кластеры по статусам
            status_display = {
                'critical': ('🔴 Критические ошибки', '#EF4444'),
                'warning': ('🟡 Предупреждения', '#F59E0B'),
                'healthy': ('✅ Пройдено', '#10B981'),
                'unknown': ('❓ Неизвестно', '#6B7280')
            }

            for status_key, (label, color) in status_display.items():
                clusters = clusters_by_status[status_key]
                if clusters:
                    with st.expander(f"{label} ({len(clusters)})", expanded=False):
                        for cluster_name in sorted(clusters):
                            st.write(f"• {cluster_name}")

            # Дополнительно показываем кластеры с предупреждениями
            clusters_with_warnings = []
            for cs in dashboard_data['cluster_statuses']:
                if cs.get('warning_count', 0) > 0:
                    clusters_with_warnings.append(cs['name'])

            if clusters_with_warnings:
                with st.expander(f"⚠️ Предупреждения ({len(clusters_with_warnings)})", expanded=False):
                    for cluster_name in sorted(clusters_with_warnings):
                        st.write(f"• {cluster_name}")


        # Дополнительная информация
        st.markdown("---")
        st.caption(f"Всего кластеров: {total_clusters}")
        st.caption(f"Обновлено: {datetime.now().strftime('%H:%M')}")

st.markdown("---")


# Детали кластеров
st.markdown("## Детали кластеров")

# Поиск по кластерам
search_term = st.text_input("Поиск кластеров", placeholder="Введите имя кластера...")

if not dashboard_data.get('clusters', []):
    st.warning("Конфигурация кластеров отсутствует. Добавьте кластеры на странице информации о кластере.")
    if st.button("Добавить кластер", type="primary"):
        st.switch_page("pages/1_cluster_info.py")
else:
    # Упрощенная таблица кластеров
    cluster_data = []
    for cluster_status in dashboard_data['cluster_statuses']:
        # Упрощенные статусы без emoji
        status_map = {
            'healthy': 'Здоров',
            'warning': 'Предупреждение',
            'critical': 'Критично',
            'unknown': 'Неизвестно'
        }

        cert_status_map = {
            'valid': 'В порядке',
            'warning': 'Скоро истечет',
            'critical': 'Близко к истечению',
            'expired': 'Просрочен',
            'unknown': 'Неизвестно'
        }

        cert_display = cert_status_map.get(cluster_status['cert_status'], 'Неизвестно')
        if cluster_status['cert_days_remaining'] is not None:
            cert_display += f" ({cluster_status['cert_days_remaining']} д.)"

        last_scan = "Не проверялся"
        if cluster_status['last_scan']:
            # Конвертируем строку timestamp обратно в datetime для форматирования
            last_scan_dt = datetime.fromisoformat(cluster_status['last_scan'])
            last_scan = last_scan_dt.strftime("%m-%d %H:%M")

        cluster_data.append({
            "Кластер": cluster_status['name'],
            "Статус": status_map[cluster_status['status']],
            "Узлы": cluster_status['node_count'],
            "Сертификат": cert_display,
            "Последняя проверка": last_scan,
            "Критично": cluster_status['critical_count'],
            "Предупреждения": cluster_status['warning_count']
        })

    # Фильтрация
    if search_term:
        cluster_data = [row for row in cluster_data if search_term.lower() in row["Кластер"].lower()]

    if cluster_data:
        cluster_df = pd.DataFrame(cluster_data)
        st.dataframe(
            cluster_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Кластер": st.column_config.TextColumn("Кластер", width="medium"),
                "Статус": st.column_config.TextColumn("Статус", width="small"),
                "Узлы": st.column_config.NumberColumn("Узлы", width="small"),
                "Сертификат": st.column_config.TextColumn("Сертификат", width="medium"),
                "Последняя проверка": st.column_config.TextColumn("Последняя проверка", width="medium"),
                "Критично": st.column_config.NumberColumn("Критично", width="small"),
                "Предупреждения": st.column_config.NumberColumn("Предупреждения", width="small")
            }
        )
    else:
        st.info("Кластеры не найдены")

    # Быстрые действия
    st.markdown("### Действия")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Запустить инспекцию", type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")

    with col2:
        if st.button("Просмотр отчёта"):
            st.switch_page("pages/3_inspect_report.py")

    with col3:
        if st.button("Управление кластером"):
            st.switch_page("pages/1_cluster_info.py")


# Последние проверки
st.markdown("## Последние проверки")

if recent_results:
    scan_records = []
    for result in recent_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")

        critical = result.get('critical', 0)
        warning = result.get('warning', 0)

        if critical > 0:
            status = 'Критично'
        elif warning > 0:
            status = 'Предупреждение'
        else:
            status = 'OK'

        scan_records.append({
            "Время": time_str,
            "Кластер": result['cluster_name'],
            "Тип": result['inspection_type'],
            "Статус": status,
            "Критично": critical,
            "Предупреждения": warning
        })

    scan_df = pd.DataFrame(scan_records)
    st.dataframe(scan_df, use_container_width=True, hide_index=True)
else:
    st.info("Записи об инспекциях отсутствуют")


# Нижний колонтитул
st.markdown("---")
st.caption(f"KubeEye {VERSION} | Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
