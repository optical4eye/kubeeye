#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Страница отчётов проверки кластера Kubernetes - переработанная версия
Предоставление улучшенного пользовательского опыта и более ясного интерфейса управления отчётами
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
    """Декоратор для измерения времени выполнения функций"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time
        if execution_time > 1.0:  # Логировать только медленные операции
            st.info(f"{func.__name__} выполнен за {execution_time:.2f} сек")

        return result
    return wrapper

# Настройка страницы
st.set_page_config(
    page_title="Отчёты проверки - kubeeye",
    layout="wide"
)


# Минималистичные стили
st.markdown("""
<style>
.stDataFrame { font-size: 14px; }
.stButton > button { padding: 6px 12px; }
</style>
""", unsafe_allow_html=True)


# Добавление корневой директории проекта в путь Python
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Импорт утилит
from utils.common import initialize_page
from utils.cluster_config import list_clusters
from utils.inspection_result import list_results, load_result
from components.ui.result_display import display_inspection_results
from components.ui.result_display import parse_opa_violations_to_table, display_opa_violations_table

# Конфигурация для очистки отчётов
CONFIG_FILE = Path(__file__).parent.parent / "data" / "cleanup_config.json"
DEFAULT_RETENTION_DAYS = 14
DEFAULT_AUTO_CLEANUP = False

# Environment variable for retention days
ENV_RETENTION_DAYS = "KUBEYE_REPORT_RETENTION_DAYS"

def load_cleanup_config() -> dict:
    """Загрузить конфигурацию очистки"""
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
    """Сохранить конфигурацию очистки"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def safe_display_opa_violations_table(violations_data, show_expander=False, table_key=None):
    """Безопасный вызов функции display_opa_violations_table с учётом совместимости параметров"""
    try:
        if table_key:
            return display_opa_violations_table(violations_data, show_expander=show_expander, table_key=table_key)
        else:
            return display_opa_violations_table(violations_data, show_expander=show_expander)
    except TypeError:
        return display_opa_violations_table(violations_data, show_expander=show_expander)


def cleanup_old_reports(retention_days: int) -> tuple[int, int]:
    """Очистить старые отчёты старше retention_days дней

    Returns:
        tuple: (удалено_файлов, освобождено_места_в_байтах)
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
            # Проверяем дату изменения файла
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
    """Отобразить секцию очистки старых отчётов"""
    with st.expander("Очистка старых отчётов", expanded=False):
        # Загрузить текущую конфигурацию
        config = load_cleanup_config()
        retention_days = config.get('retention_days', DEFAULT_RETENTION_DAYS)

        # Настройки
        st.markdown("#### Настройки периода хранения")

        # Показать источник настройки
        source = config.get('source', 'default')
        if source == 'env':
            st.info(f"Настройка установлена через переменную окружения `{ENV_RETENTION_DAYS}={retention_days}` дней")
            st.number_input(
                "Сохранять отчёты (дней)",
                min_value=1,
                max_value=365,
                value=retention_days,
                disabled=True,
                help="Значение установлено через переменную окружения"
            )
        else:
            retention_days_input = st.number_input(
                "Сохранять отчёты (дней)",
                min_value=1,
                max_value=365,
                value=retention_days,
                help="Отчёты старше этого периода удаляются автоматически"
            )

            # Сохранить настройки
            if st.button("Сохранить настройки"):
                config['retention_days'] = retention_days_input
                save_cleanup_config(config)
                st.success("Настройки сохранены")
                st.rerun()

        # Ручная очистка
        if st.button("Очистить старые отчёты сейчас"):
            with st.spinner("Очистка..."):
                deleted_count, freed_space = cleanup_old_reports(retention_days)
                if deleted_count > 0:
                    freed_mb = freed_space / (1024 * 1024)
                    st.success(f"Удалено {deleted_count} старых отчётов, освобождено {freed_mb:.1f} MB")
                else:
                    st.info("Старых отчётов для удаления не найдено")

        st.info("Старые отчёты удаляются автоматически при открытии этой страницы")


def get_reports_list(limit=500, force_refresh=False, _version="v2"):
    """Получить список отчётов без кэширования"""
    return list_results(limit=limit, order_by='timestamp DESC')

def display_reports_overview():
    """Отобразить обзор страницы отчётов"""
    st.markdown("Просмотр и управление отчётами по всем кластерам")

    # Кэширование отключено

    # Убрана кнопка обновления для минималистичного дизайна

    clusters = list_clusters()
    all_results = get_reports_list(limit=500)  # Используем кэшированную функцию

    if not all_results:
        st.info("Нет доступных отчётов. Выполните проверку для создания отчётов.")
        if st.button("Выполнить проверку", type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")
        return

    # Секция очистки старых отчётов
    display_cleanup_section(all_results)

    st.divider()

    # Информация о количестве отчётов
    st.info(f"Найдено {len(all_results)} отчётов")

    # Минималистичный дизайн - убраны лишние предупреждения

    # Простые фильтры
    col1, col2 = st.columns(2)
    with col1:
        selected_cluster = st.selectbox("Кластер", ["Все"] + clusters)
    with col2:
        date_filter = st.selectbox("Период", ["Все", "Сегодня", "Последние 7 дней", "Последние 30 дней"])

    filtered_results = all_results
    if selected_cluster != "Все":
        filtered_results = [r for r in filtered_results if r["cluster_name"] == selected_cluster]

    now = datetime.now()
    if date_filter != "Все":
        if date_filter == "Сегодня":
            filtered_results = [r for r in filtered_results if
                               datetime.fromisoformat(r['timestamp']).date() == now.date()]
        elif date_filter == "Последние 7 дней":
            week_ago = now - timedelta(days=7)
            filtered_results = [r for r in filtered_results if
                               datetime.fromisoformat(r['timestamp']) >= week_ago]
        elif date_filter == "Последние 30 дней":
            month_ago = now - timedelta(days=30)
            filtered_results = [r for r in filtered_results if
                               datetime.fromisoformat(r['timestamp']) >= month_ago]

    if filtered_results:
        display_statistics_overview(filtered_results)
        display_reports_table(filtered_results)
    else:
        st.info("Нет отчётов по выбранным критериям")


def display_statistics_overview(filtered_results):
    """Показать обзор статистики"""
    st.markdown("### Статистика")

    total_reports = len(filtered_results)
    total_critical = sum(r['critical'] for r in filtered_results)
    total_warnings = sum(r['warning'] for r in filtered_results)
    total_info = sum(r.get('info', 0) for r in filtered_results)  # Добавить подсчёт info ошибок
    total_passed = sum(r['passed'] for r in filtered_results)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Отчётов", total_reports)
    with col2:
        st.metric("Критично", total_critical)
    with col3:
        st.metric("Предупреждения", total_warnings)
    with col4:
        st.metric("Прочее", total_info)
    with col5:
        st.metric("Успешно", total_passed)
    with col6:
        latest_report = max(filtered_results, key=lambda x: x['timestamp'])
        latest_time = datetime.fromisoformat(latest_report['timestamp']).strftime('%m-%d %H:%M')
        st.metric("Последний", latest_time)


def display_reports_table(filtered_results):
    """Показать список отчётов с возможностью выбора"""
    st.markdown("### Список отчётов")

    if not filtered_results:
        st.info("Нет доступных отчётов")
        return

    sorted_results = sorted(filtered_results,
                           key=lambda x: (-x['critical'], -x['warning'], -x.get('info', 0), x['timestamp']),
                           reverse=True)

    df_data = []
    for result in sorted_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        critical_count = result['critical']
        warning_count = result['warning']
        info_count = result.get('info', 0)  # Добавить info ошибки
        total_exceptions = critical_count + warning_count + info_count

        df_data.append({
            "ID": result['result_id'],
            "Кластер": result['cluster_name'],
            "Время": timestamp.strftime('%m-%d %H:%M'),
            "Тип": "Немедленная" if result['inspection_type'] == 'immediate' else "Плановая",
            "Статус": "Ошибка" if total_exceptions > 0 else "OK",
            "Критично": critical_count,
            "Предупреждения": warning_count,
            "Прочее": info_count,
            "Успешно": result['passed']
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
            "Кластер": st.column_config.TextColumn("Кластер"),
            "Время": st.column_config.TextColumn("Время"),
            "Тип": st.column_config.TextColumn("Тип"),
            "Статус": st.column_config.TextColumn("Статус"),
            "Критично": st.column_config.NumberColumn("Критично"),
            "Предупреждения": st.column_config.NumberColumn("Предупреждения"),
            "Прочее": st.column_config.NumberColumn("Прочее"),
            "Успешно": st.column_config.NumberColumn("Успешно")
        }
    )

    if len(event.selection.rows) > 0:
        selected_row = event.selection.rows[0]
        selected_result = sorted_results[selected_row]
        st.session_state.selected_report_id = selected_result['result_id']
        st.session_state.view_mode = "operations"
        st.rerun()


def delete_report(report_id):
    """Удаление файла отчёта"""
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
    """Отобразить страницу операций с отчётом"""
    if st.button("Вернуться к списку отчётов"):
        st.session_state.view_mode = "list"
        st.rerun()

    report_data = load_result(report_id)
    if not report_data:
        st.error("Не удалось загрузить данные отчёта")
        return

    st.markdown(f"### Центр операций с отчётом")

    col1, col2 = st.columns([3, 1])
    with col1:
        timestamp = datetime.fromisoformat(report_data['timestamp'])
        st.markdown(f"""
        **ID отчёта:** `{report_id}`
        **Кластер:** {report_data['cluster_name']}
        **Время проверки:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        **Тип:** {'Немедленная проверка' if report_data['inspection_type'] == 'immediate' else 'Плановая проверка'}
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
                st.error(f"Критических ошибок: {exception_critical_count}")
            if exception_warning_count > 0:
                st.warning(f"Предупреждений: {exception_warning_count}")
        else:
            st.success("Все проверки пройдены")
        st.info(f"Всего: {len(all_items)}")

    st.divider()

    st.markdown("### Операции")

    col1, col2, col3 = st.columns(3)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Просмотр деталей", type="primary", width='stretch'):
            st.session_state.view_mode = "detail"
            st.rerun()

    with col2:
        if st.button("Экспорт JSON", width='stretch'):
            export_and_download(report_id, "json", "JSON")

    with col3:
        if st.button("Экспорт Excel", width='stretch'):
            export_and_download(report_id, "excel", "Excel")

    with col4:
        if st.button("Экспорт PDF", width='stretch'):
            success, message = export_report(report_id, "pdf")
            if success:
                st.success("PDF отчет успешно создан!")
                try:
                    with open(message, "rb") as f:
                        pdf_data = f.read()
                    st.download_button(
                        label="Скачать PDF отчет",
                        data=pdf_data,
                        file_name=f"{report_id}.pdf",
                        mime="application/pdf",
                        type="secondary",
                        width='stretch'
                    )
                    # Удаляем файл из папки exports после предоставления для скачивания
                    os.remove(message)
                except Exception as e:
                    st.error(f"Ошибка при чтении PDF файла: {str(e)}")
            else:
                if "reportlab" in message:
                    st.error(f"{message}")
                    st.info("Установите reportlab для PDF экспорта: `pip install reportlab`")
                else:
                    st.error(f"{message}")

    st.markdown("#### Удаление")
    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Удаление необратимо, будьте осторожны")

    with col2:
        confirm_key = f"confirm_delete_{report_id}"
        if st.session_state.get(confirm_key, False):
            if st.button("Подтвердить удаление", type="primary", width='stretch'):
                try:
                    delete_report(report_id)
                    st.success(f"Отчёт {report_id} удалён")
                    if confirm_key in st.session_state:
                        del st.session_state[confirm_key]
                    st.session_state.view_mode = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка при удалении: {str(e)}")
        else:
            if st.button("Удалить", width='stretch'):
                st.session_state[confirm_key] = True
                st.rerun()

    if st.session_state.get(confirm_key, False):
        st.warning("Нажмите подтверждение для удаления отчёта")


def display_report_detail(report_id):
    """Отобразить детали отчёта"""
    if st.button("Вернуться к операциям"):
        st.session_state.view_mode = "operations"
        st.rerun()

    report_data = load_result(report_id)
    if not report_data:
        st.error("Не удалось загрузить данные отчёта")
        return

    st.markdown(f"## Детали отчёта")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        **ID отчёта:** `{report_id}`
        **Кластер:** {report_data['cluster_name']}
        **Время:** {datetime.fromisoformat(report_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
        **Тип:** {'Немедленная проверка' if report_data['inspection_type'] == 'immediate' else 'Плановая проверка'}
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
            st.error(f"Найдено {exception_count} критических ошибок")
        else:
            st.success(f"Все пройдено ({passed_count} позиций)")

    st.divider()

    display_inspection_items(all_items, report_id=report_id)


def display_report_preview(report_id):
    """Показать быструю предпросмотр отчёта - версия с упрощённой системой статусов"""
    if st.button("Назад"):
        st.session_state.view_mode = "list"
        st.rerun()

    st.markdown(f"## Предпросмотр отчёта - {report_id}")

    report_data = load_result(report_id)
    if not report_data:
        st.error("Не удалось загрузить данные отчёта")
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
            st.error(f"Критические ошибки: {len(exception_critical)}")
        if exception_warning:
            st.warning(f"Предупреждения: {len(exception_warning)}")
        if exception_other:
            st.info(f"Другие ошибки: {len(exception_other)}")

    with col2:
        st.success(f"Успешно: {len(passed_items)}")
        st.info(f"Всего: {len(all_items)}")

    if exception_critical:
        st.markdown("### Критические ошибки")
        for item in exception_critical[:5]:
            st.error(f"**{item.get('name', 'Неизвестный пункт')}:** {item.get('description', '')}")
        if len(exception_critical) > 5:
            st.info(f"И ещё {len(exception_critical) - 5} критических ошибок, смотрите полный отчёт для подробностей")
    elif exception_warning:
        st.markdown("### Предупреждения")
        for item in exception_warning[:3]:
            st.warning(f"**{item.get('name', 'Неизвестный пункт')}:** {item.get('description', '')}")
        if len(exception_warning) > 3:
            st.info(f"И ещё {len(exception_warning) - 3} предупреждений, смотрите полный отчёт для подробностей")

    if st.button("Посмотреть полный отчёт", type="primary"):
        st.session_state.view_mode = "detail"
        st.rerun()

def display_inspection_items(items, report_id=None):
    """Отобразить детали проверок - версия с упрощённой системой статусов"""
    # Классификация по новому статусу: пройдено vs ошибки (с разделением по степени серьёзности)
    passed_items = [item for item in items if item.get('status') == 'passed']
    exception_critical = [item for item in items
                         if item.get('status') == 'exception' and item.get('severity') == 'critical']
    exception_warning = [item for item in items
                        if item.get('status') == 'exception' and item.get('severity') == 'warning']
    exception_info = [item for item in items
                     if item.get('status') == 'exception' and item.get('severity') in ['info', 'error'] or
                     (item.get('status') == 'exception' and item.get('severity') not in ['critical', 'warning'])]

    # Создание вкладок
    tab_names = []
    tab_data = []

    # Предпочтительно отображать критические ошибки
    if exception_critical:
        tab_names.append(f"Критические ошибки ({len(exception_critical)})")
        tab_data.append(exception_critical)

    if exception_warning:
        tab_names.append(f"Предупреждения ({len(exception_warning)})")
        tab_data.append(exception_warning)

    if exception_info:
        tab_names.append(f"Прочие ошибки ({len(exception_info)})")
        tab_data.append(exception_info)

    # В конце отображать пройденные проверки
    if passed_items:
        tab_names.append(f"Пройдено ({len(passed_items)})")
        tab_data.append(passed_items)

    if tab_names:
        tabs = st.tabs(tab_names)
        for i, (tab, data) in enumerate(zip(tabs, tab_data)):
            with tab:
                display_items_list(data, tab_names[i].startswith("Пройдено"), report_id=report_id, tab_name=tab_names[i])


def display_items_list(items, is_passed=False, report_id=None, tab_name=None):
    """Отобразить список проверок - версия с упрощённой системой статусов"""
    if not items:
        st.info("В этой категории пока нет элементов")
        return

    # Для пройденных элементов свёрнутое отображение по умолчанию
    for idx, item in enumerate(items):
        title = f"{item.get('name', 'Неизвестный пункт проверки')}"
        expanded = not is_passed and item.get('severity') == 'critical'
        with st.expander(title, expanded=expanded):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Описание:** {item.get('description', 'нет')}")
                details = item.get('details', '')
                if details:
                    if 'violations' in item and isinstance(item['violations'], list):
                        st.markdown("**Нарушения ресурсов:**")
                        import hashlib
                        base = f"{item.get('name','')}_{item.get('description','')[:50]}_{report_id or ''}_{tab_name or ''}_{idx}"
                        item_key = hashlib.md5(base.encode()).hexdigest()[:12]
                        safe_display_opa_violations_table(item['violations'], show_expander=False, table_key=item_key)
                    else:
                        st.markdown("**Детали:**")
                        st.text(details)
            with col2:
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'info')
                if status == 'exception':
                    if severity == 'critical':
                        st.error("Критическая ошибка")
                    elif severity == 'warning':
                        st.warning("Обычная ошибка")
                    else:
                        st.info("Прочая ошибка")
                elif status == 'passed':
                    st.success("Пройдено")
                else:
                    st.info("Неизвестное состояние")
            solution = item.get('solution', '')
            if solution:
                st.markdown("**Рекомендации по решению:**")
                st.info(solution)


def display_export_page(report_id):
    """Показать страницу экспорта - оптимизированная версия"""
    if st.button("Назад"):
        st.session_state.view_mode = "list"
        st.rerun()

    st.markdown(f"### Экспорт отчёта - {report_id}")

    # Быстрый экспорт
    st.markdown("#### Быстрый экспорт")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Экспорт в JSON", width='stretch'):
            export_and_download(report_id, "json", "JSON")

    with col2:
        if st.button("Экспорт в Excel", width='stretch'):
            export_and_download(report_id, "excel", "Excel")

    st.divider()

    # Пользовательские опции экспорта
    st.markdown("#### Настройки экспорта")
    col1, col2 = st.columns([2, 1])

    with col1:
        export_format = st.selectbox(
            "Выберите формат экспорта",
            ["JSON", "Excel"],
            help="Выберите формат для экспорта отчёта"
        )

        include_passed = st.checkbox("Включить пройденные проверки", value=False,
                                    help="По умолчанию экспортируются только ошибки, отметьте для включения всех проверок")

        include_details = st.checkbox("Включить детали", value=True,
                                     help="Включать подробную информацию об ошибках и рекомендации")

    with col2:
        st.markdown("**Предварительный просмотр содержимого экспорта**")
        report_data = load_result(report_id)
        if report_data:
            total_items = 0
            exception_items = 0

            if 'inspection_results' in report_data:
                for inspector_type, inspector_result in report_data['inspection_results'].items():
                    items = inspector_result.get('items', [])
                    total_items += len(items)
                    exception_items += len([item for item in items if item.get('status') != 'passed'])

            st.metric("Всего проверок", total_items)
            st.metric("Ошибок", exception_items)

            if include_passed:
                st.info(f"Будут экспортированы {total_items} записей")
            else:
                st.info(f"Будут экспортированы {exception_items} ошибок")

    if st.button("Начать экспорт", type="primary"):
        export_and_download(report_id, export_format.lower(), export_format,
                            include_passed, include_details)


def export_and_download(report_id, format_type, format_name, include_passed=False, include_details=True):
    """Выполнить экспорт и предоставить файл для скачивания"""
    try:
        from utils.inspection_result import export_report

        success, file_path = export_report(report_id, format_type)

        if success:
            st.success(f"Экспорт в {format_name} выполнен успешно!")

            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                mime_types = {
                    "json": "application/json",
                    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
                st.download_button(
                    label=f"Скачать файл {format_name}",
                    data=file_data,
                    file_name=os.path.basename(file_path),
                    mime=mime_types.get(format_type, "application/octet-stream"),
                    type="secondary",
                    width='stretch'
                )
                # Удаляем файл из папки exports после предоставления для скачивания
                os.remove(file_path)
                file_size = len(file_data) / 1024
                st.caption(f"Размер файла: {file_size:.1f} КБ")
            except Exception as e:
                st.error(f"Ошибка при чтении файла: {str(e)}")
        else:
            st.error(f"Экспорт не удался: {file_path}")
    except Exception as e:
        st.error(f"Ошибка при экспорте: {str(e)}")


def main():
    """Главная функция"""
    initialize_page(
        title="Отчёты проверки",
        page_title="Отчёты проверки",
        page_subtitle="Обзор состояния кластеров"
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
            st.error("Отчёт не выбран")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "detail":
        if st.session_state.selected_report_id:
            display_report_detail(st.session_state.selected_report_id)
        else:
            st.error("Отчёт не выбран")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "preview":
        if st.session_state.selected_report_id:
            display_report_preview(st.session_state.selected_report_id)
        else:
            st.error("Отчёт не выбран")
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
