#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeEye - Инструмент для инспекции кластера Kubernetes


Этот файл является точкой входа приложения, инициализирует интерфейс и отображает содержимое главной страницы.
"""


# Импорт стандартных библиотек
import os
import sys
import json
from datetime import datetime
from pathlib import Path


# Импорт сторонних библиотек
import streamlit as st
import pandas as pd


# Настройка конфигурации страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="KubeEye - Инструмент для инспекции кластера Kubernetes",
    page_icon="🔍",
    layout="wide"
)


# Импорт модулей проекта
from utils.common import initialize_page
from utils.cluster_config import list_clusters, get_cluster
from utils.inspection_result import list_results, get_latest_result_by_cluster
from utils.rule_loader import load_rules
from utils.version import VERSION, APP_NAME, APP_DESCRIPTION, RELEASE_DATE
from utils.cert_checker import get_cluster_cert_status


# Конфигурация страницы уже настроена выше, теперь инициализируем остальные компоненты страницы
initialize_page(
    title="Обзор инспекций",
    icon="📊",
    page_title="Обзор инспекции кластера",
    page_subtitle=" Обзор инспекций кластера Kubernetes"
)


# Загрузка списка кластеров
clusters = list_clusters()


# Загрузка правил - все правила теперь используют единый формат утверждений
node_rules = load_rules('node')
prometheus_rules = load_rules('prometheus')
opa_rules = load_rules('opa')


# Подсчет общего количества правил
total_rules = len(node_rules) + len(prometheus_rules) + len(opa_rules)


# Установка упрощенного стиля
st.markdown("""
<style>
.status-healthy { color: #28a745; font-weight: bold; }
.status-warning { color: #ffc107; font-weight: bold; }
.status-critical { color: #dc3545; font-weight: bold; }
.status-unknown { color: #6c757d; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# Получение данных
clusters = list_clusters()
all_results = list_results()


# Подсчет статистики
total_clusters = len(clusters)


# Результаты инспекций за последние 24 часа
recent_scans = 0
recent_issues = 0


if all_results:
    # Подсчет данных за последние 24 часа
    now = datetime.now()
    for result in all_results:
        result_time = datetime.fromisoformat(result['timestamp'])
        if (now - result_time).total_seconds() < 24 * 3600:  # в пределах 24 часов
            recent_scans += 1
            recent_issues += result.get('critical', 0) + result.get('warning', 0)


# Получение последнего статуса каждого кластера
cluster_statuses = {}
for cluster_name in clusters:
    latest_result = None
    for result in all_results:
        if result['cluster_name'] == cluster_name:
            latest_result = result
            break

    if latest_result:
        critical = latest_result.get('critical', 0)
        warning = latest_result.get('warning', 0)

        if critical > 0:
            status = 'critical'
        elif warning > 0:
            status = 'warning'
        else:
            status = 'healthy'
    else:
        status = 'unknown'

    cluster_statuses[cluster_name] = {
        'status': status,
        'latest_result': latest_result
    }


# Вверху обозрение статистики
st.markdown("### 📊 Обзор")
cols = st.columns(5)


with cols[0]:
    st.metric(
        label="Общее число кластеров",
        value=total_clusters,
        delta=None
    )


with cols[1]:
    st.metric(
        label="Число инспекций за 24 часа",
        value=recent_scans,
        delta=None
    )


with cols[2]:
    st.metric(
        label="Обнаруженные проблемы",
        value=recent_issues,
        delta=None
    )


with cols[3]:
    latest_scan_time = "Никогда не запускалась"
    if all_results:
        latest_time = datetime.fromisoformat(all_results[0]['timestamp'])
        latest_scan_time = latest_time.strftime("%m-%d %H:%M")

    st.metric(
        label="Последняя инспекция",
        value=latest_scan_time,
        delta=None
    )


with cols[4]:
    st.metric(
        label="Общее число правил инспекции",
        value=total_rules,
        delta=None
    )


st.markdown("---")


# Основная часть - таблица статусов кластера
st.markdown("### 🏗️ Детали статусов кластера")


if not clusters:
    st.warning("📝 Конфигурация кластеров отсутствует, пожалуйста, добавьте конфигурации на странице \"Информация о кластере\".")
    if st.button("➕ Добавить кластер сейчас", type="primary"):
        st.switch_page("pages/1_cluster_info.py")
else:
    # Подготовка данных таблицы статусов кластера
    cluster_data = []

    for cluster_name in clusters:
        status_info = cluster_statuses[cluster_name]
        status = status_info['status']
        latest_result = status_info['latest_result']

        # Получение конфигурации кластера
        cluster_config = get_cluster(cluster_name)
        nodes_count = len(cluster_config.get_nodes())

        # Проверка статуса сертификата
        kubeconfig = cluster_config.get_kubeconfig()
        cert_status_info = {'status': 'unknown', 'days_remaining': None}
        if kubeconfig:
            cert_status_info = get_cluster_cert_status(cluster_name, kubeconfig)

        # Отображение статуса
        status_icons = {
            'healthy': '✅ Здоров',
            'warning': '⚠️ Предупреждение',
            'critical': '❌ Критично',
            'unknown': '❓ Неизвестно'
        }

        cert_status_text = {
            'valid': '✅ В порядке',
            'warning': '⚠️ Скоро истечет',
            'critical': '🔴 Близко к истечению',
            'expired': '❌ Просрочен',
            'unknown': '❓ Неизвестно'
        }

        cert_status = cert_status_info['status']
        days_remaining = cert_status_info.get('days_remaining')

        cert_display = cert_status_text.get(cert_status, '❓ Неизвестно')
        if days_remaining is not None and days_remaining >= 0:
            cert_display += f" ({days_remaining} дней)"
        elif days_remaining is not None and days_remaining < 0:
            cert_display += f" (Просрочен на {abs(days_remaining)} дней)"

        # Время последней инспекции
        last_scan = "Никогда не инспектировался"
        if latest_result:
            scan_time = datetime.fromisoformat(latest_result['timestamp'])
            last_scan = scan_time.strftime("%m-%d %H:%M")

        # Статистика результатов инспекции
        critical_count = latest_result.get('critical', 0) if latest_result else 0
        warning_count = latest_result.get('warning', 0) if latest_result else 0
        passed_count = latest_result.get('passed', 0) if latest_result else 0

        cluster_data.append({
            "Название кластера": f"**{cluster_name}**",
            "Статус": status_icons[status],
            "Количество узлов": nodes_count,
            "Срок действия kubeconfig": cert_display,
            "Последняя инспекция": last_scan,
            "Критичные проблемы": critical_count,
            "Предупреждения": warning_count,
            "Успешно": passed_count
        })

    # Отображение таблицы статусов кластера
    cluster_df = pd.DataFrame(cluster_data)
    st.table(cluster_df)

    # Быстрые действия
    st.markdown("#### 🚀 Быстрые действия")
    cols = st.columns(3)

    with cols[0]:
        if st.button("🔍 Запустить инспекцию", width='stretch', type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")

    with cols[1]:
        if st.button("📊 Просмотр отчёта", width='stretch'):
            st.switch_page("pages/3_inspect_report.py")

    with cols[2]:
        if st.button("⚙️ Управление кластером", width='stretch'):
            st.switch_page("pages/1_cluster_info.py")


# Таблица последних записей инспекции
st.markdown("### 📈 Последние записи инспекции")


if all_results:
    # Подготовка данных для таблицы записей инспекции
    recent_results = all_results[:10]  # последние 10 записей

    scan_records = []
    for result in recent_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")

        # Определение статуса
        critical = result.get('critical', 0)
        warning = result.get('warning', 0)
        passed = result.get('passed', 0)

        if critical > 0:
            status = '❌ Критично'
        elif warning > 0:
            status = '⚠️ Предупреждение'
        else:
            status = '✅ В порядке'

        scan_records.append({
            "Время": time_str,
            "Кластер": f"**{result['cluster_name']}**",
            "Тип": result['inspection_type'],
            "Статус": status,
            "Критичные проблемы": critical,
            "Предупреждения": warning,
            "Успешно": passed
        })

    scan_df = pd.DataFrame(scan_records)
    st.table(scan_df)
else:
    st.info("📋 Записи об инспекциях отсутствуют, после первой инспекции здесь появится история.")


# Нижняя часть страницы
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; font-size: 0.85rem; padding: 1rem;">
    KubeEye {VERSION} |
    <a href="#" onclick="window.location.reload()">Обновить страницу</a> |
    Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>
""", unsafe_allow_html=True)
