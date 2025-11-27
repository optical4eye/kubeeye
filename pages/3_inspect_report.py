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


# Настройка страницы
st.set_page_config(
    page_title="Отчёты проверки - kubeeye",
    page_icon="📊",
    layout="wide"
)


# Добавление пользовательских CSS стилей
st.markdown("""
<style>
    /* Оптимизация отступов и выравнивания строк в таблице */
    .row-container {
        padding: 8px 0;
        border-bottom: 1px solid #e0e0e0;
    }

    /* Стиль маленьких кнопок */
    .stButton > button {
        padding: 4px 8px;
        font-size: 12px;
        height: 28px;
        margin: 1px;
    }

    /* Стиль заголовков таблицы */
    .table-header {
        font-weight: bold;
        padding: 8px 0;
        border-bottom: 2px solid #ddd;
        background-color: #f8f9fa;
    }

    /* Стиль меток состояния */
    .status-normal {
        color: #28a745;
        font-weight: bold;
    }

    .status-error {
        color: #dc3545;
        font-weight: bold;
    }

    /* Выделение чисел */
    .number-highlight {
        font-weight: bold;
        color: #007bff;
    }
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


def safe_display_opa_violations_table(violations_data, show_expander=False, table_key=None):
    """Безопасный вызов функции display_opa_violations_table с учётом совместимости параметров"""
    try:
        if table_key:
            return display_opa_violations_table(violations_data, show_expander=show_expander, table_key=table_key)
        else:
            return display_opa_violations_table(violations_data, show_expander=show_expander)
    except TypeError:
        return display_opa_violations_table(violations_data, show_expander=show_expander)


def display_reports_overview():
    """Отобразить обзор страницы отчётов"""
    st.markdown("Просмотр и управление отчётами по всем кластерам, быстрое выявление проблем и получение рекомендаций по их решению.")
    st.caption("💡 Система автоматически хранит отчёты за последние 30 дней, старые отчёты удаляются для экономии места")

    clusters = list_clusters()
    all_results = list_results()

    if hasattr(st.session_state, 'last_result_path') and st.session_state.last_result_path:
        st.success(f"🆕 Найден последний результат проверки: {os.path.basename(st.session_state.last_result_path)}")
        if st.button("🔍 Просмотр последнего результата", type="primary"):
            result_id = None
            if hasattr(st.session_state, 'last_result_id'):
                result_id = st.session_state.last_result_id
            if not result_id and all_results:
                latest_result = max(all_results, key=lambda x: x['timestamp'])
                result_id = latest_result['result_id']
            if not result_id and st.session_state.last_result_path:
                try:
                    with open(st.session_state.last_result_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    result_id = data.get('result_id')
                except Exception:
                    pass
            if result_id:
                st.session_state.selected_report_id = result_id
                st.session_state.view_mode = "detail"
                st.rerun()
            else:
                st.error("❌ Не удалось получить ID последнего результата, выберите в списке отчётов")

    if not all_results:
        st.info("📭 Нет доступных отчётов. Сначала выполните проверку, чтобы создать отчёты.")
        if st.button("🚀 Выполнить проверку", type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")
        return

    st.markdown("### 🔍 Фильтры отчётов")
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_cluster = st.selectbox(
            "Выбрать кластер",
            ["Все"] + clusters,
            help="Фильтрация отчётов по кластеру"
        )

    with col2:
        inspection_types = ["Все", "immediate", "scheduled"]
        selected_type = st.selectbox(
            "Тип проверки",
            inspection_types,
            format_func=lambda x: "Немедленная" if x == "immediate" else ("Плановая" if x == "scheduled" else x)
        )

    with col3:
        date_filter = st.selectbox(
            "Временной диапазон",
            ["Все", "Сегодня", "Последние 7 дней", "Последние 30 дней"]
        )

    filtered_results = all_results
    if selected_cluster != "Все":
        filtered_results = [r for r in filtered_results if r["cluster_name"] == selected_cluster]
    if selected_type != "Все":
        filtered_results = [r for r in filtered_results if r["inspection_type"] == selected_type]

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
        st.info("🔍 Нет отчётов, соответствующих критериям")


def display_statistics_overview(filtered_results):
    """Показать обзор статистики"""
    st.markdown("### 📈 Обзор статистики")

    total_reports = len(filtered_results)
    total_exceptions = sum(r['critical'] + r['warning'] for r in filtered_results)
    total_passed = sum(r['passed'] for r in filtered_results)

    latest_report = max(filtered_results, key=lambda x: x['timestamp'])
    latest_time = datetime.fromisoformat(latest_report['timestamp']).strftime('%m-%d %H:%M')

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📄 Всего отчётов", total_reports)

    with col2:
        st.metric("⚠️ Ошибок", total_exceptions,
                  delta=f"-{total_exceptions}" if total_exceptions > 0 else None,
                  delta_color="inverse")

    with col3:
        st.metric("✅ Успешно", total_passed,
                  delta=f"+{total_passed}" if total_passed > 0 else None)

    with col4:
        st.metric("🕒 Последний отчёт", latest_time)


def display_reports_table(filtered_results):
    """Показать список отчётов с возможностью выбора"""
    st.markdown("### 📋 Список отчётов")
    st.markdown("💡 *Нажмите на ID отчёта для просмотра деталей и действий*")

    if not filtered_results:
        st.info("📭 Нет доступных отчётов")
        return

    sorted_results = sorted(filtered_results,
                           key=lambda x: (-(x['critical'] + x['warning']), x['timestamp']),
                           reverse=True)

    df_data = []
    for result in sorted_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        total_exceptions = result['critical'] + result['warning']
        report_id = result['result_id']

        df_data.append({
            "📄 ID отчёта": report_id,
            "🏢 Кластер": result['cluster_name'],
            "⏰ Время проверки": timestamp.strftime('%m-%d %H:%M'),
            "🔄 Тип": "⚡ Немедленная" if result['inspection_type'] == 'immediate' else "⏲️ Плановая",
            "📊 Статус": "🔴 Ошибка" if total_exceptions > 0 else "🟢 Норма",
            "⚠️ Ошибок": total_exceptions,
            "✅ Успешно": result['passed'],
            "📈 Всего": total_exceptions + result['passed']
        })

    df = pd.DataFrame(df_data)

    event = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "📄 ID отчёта": st.column_config.TextColumn("📄 ID отчёта", help="Нажмите на строку для просмотра деталей и действий"),
            "🏢 Кластер": st.column_config.TextColumn("🏢 Кластер"),
            "⏰ Время проверки": st.column_config.TextColumn("⏰ Время проверки"),
            "🔄 Тип": st.column_config.TextColumn("🔄 Тип"),
            "📊 Статус": st.column_config.TextColumn("📊 Статус"),
            "⚠️ Ошибок": st.column_config.NumberColumn("⚠️ Ошибок"),
            "✅ Успешно": st.column_config.NumberColumn("✅ Успешно"),
            "📈 Всего": st.column_config.NumberColumn("📈 Всего")
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
    if st.button("⬅️ Вернуться к списку отчётов"):
        st.session_state.view_mode = "list"
        st.rerun()

    report_data = load_result(report_id)
    if not report_data:
        st.error("❌ Не удалось загрузить данные отчёта")
        return

    st.markdown(f"### 📄 Центр операций с отчётом")

    col1, col2 = st.columns([3, 1])
    with col1:
        timestamp = datetime.fromisoformat(report_data['timestamp'])
        st.markdown(f"""
        **🏷️ ID отчёта:** `{report_id}`
        **🏢 Кластер:** {report_data['cluster_name']}
        **⏰ Время проверки:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        **📋 Тип:** {'⚡ Немедленная проверка' if report_data['inspection_type'] == 'immediate' else '⏲️ Плановая проверка'}
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
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
            else:
                status = 'unknown'

            if status == 'passed':
                passed_count += 1
            elif status == 'exception':
                exception_count += 1

        if exception_count > 0:
            st.error(f"🔴 Ошибок: {exception_count}")
        else:
            st.success("🟢 Все проверки пройдены")
        st.info(f"📊 Всего: {len(all_items)}")

    st.divider()

    st.markdown("### 🔧 Операции")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 Просмотр деталей", type="primary", width='stretch'):
            st.session_state.view_mode = "detail"
            st.rerun()

    with col2:
        if st.button("📄 Экспорт JSON", width='stretch'):
            export_and_download(report_id, "json", "JSON")

    with col3:
        if st.button("📊 Экспорт Excel", width='stretch'):
            export_and_download(report_id, "excel", "Excel")

    st.markdown("#### 🗑️ Удаление")
    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("⚠️ Удаление необратимо, будьте осторожны")

    with col2:
        confirm_key = f"confirm_delete_{report_id}"
        if st.session_state.get(confirm_key, False):
            if st.button("❌ Подтвердить удаление", type="primary", width='stretch'):
                try:
                    delete_report(report_id)
                    st.success(f"✅ Отчёт {report_id} удалён")
                    if confirm_key in st.session_state:
                        del st.session_state[confirm_key]
                    st.session_state.view_mode = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при удалении: {str(e)}")
        else:
            if st.button("🗑️ Удалить", width='stretch'):
                st.session_state[confirm_key] = True
                st.rerun()

    if st.session_state.get(confirm_key, False):
        st.warning("⚠️ Нажмите подтверждение для удаления отчёта")


def display_report_detail(report_id):
    """Отобразить детали отчёта"""
    if st.button("⬅️ Вернуться к операциям"):
        st.session_state.view_mode = "operations"
        st.rerun()

    report_data = load_result(report_id)
    if not report_data:
        st.error("❌ Не удалось загрузить данные отчёта")
        return

    st.markdown(f"## 📄 Детали отчёта")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        **🏷️ ID отчёта:** `{report_id}`
        **🖥️ Кластер:** {report_data['cluster_name']}
        **⏰ Время:** {datetime.fromisoformat(report_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
        **📋 Тип:** {'⚡ Немедленная проверка' if report_data['inspection_type'] == 'immediate' else '⏲️ Плановая проверка'}
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
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
            else:
                status = 'unknown'

            if status == 'passed':
                passed_count += 1
            elif status == 'exception':
                exception_count += 1

        if exception_count > 0:
            st.error(f"🔴 Найдено {exception_count} ошибок")
        else:
            st.success(f"🟢 Все пройдено ({passed_count} позиций)")

    st.divider()

    display_inspection_items(all_items, report_id=report_id)


def display_report_preview(report_id):
    """Показать быструю предпросмотр отчёта - версия с упрощённой системой статусов"""
    if st.button("⬅️ Назад"):
        st.session_state.view_mode = "list"
        st.rerun()

    st.markdown(f"## 👁️ Предпросмотр отчёта - {report_id}")

    report_data = load_result(report_id)
    if not report_data:
        st.error("❌ Не удалось загрузить данные отчёта")
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
            st.error(f"🔴 Критические ошибки: {len(exception_critical)}")
        if exception_warning:
            st.warning(f"🟡 Предупреждения: {len(exception_warning)}")
        if exception_other:
            st.info(f"ℹ️ Другие ошибки: {len(exception_other)}")

    with col2:
        st.success(f"✅ Успешно: {len(passed_items)}")
        st.info(f"📊 Всего: {len(all_items)}")

    if exception_critical:
        st.markdown("### 🚨 Критические ошибки")
        for item in exception_critical[:5]:
            st.error(f"**{item.get('name', 'Неизвестный пункт')}:** {item.get('description', '')}")
        if len(exception_critical) > 5:
            st.info(f"И ещё {len(exception_critical) - 5} критических ошибок, смотрите полный отчёт для подробностей")
    elif exception_warning:
        st.markdown("### ⚠️ Предупреждения")
        for item in exception_warning[:3]:
            st.warning(f"**{item.get('name', 'Неизвестный пункт')}:** {item.get('description', '')}")
        if len(exception_warning) > 3:
            st.info(f"И ещё {len(exception_warning) - 3} предупреждений, смотрите полный отчёт для подробностей")

    if st.button("📋 Посмотреть полный отчёт", type="primary"):
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
        tab_names.append(f"🔴 Критические ошибки ({len(exception_critical)})")
        tab_data.append(exception_critical)

    if exception_warning:
        tab_names.append(f"🟡 Обычные ошибки ({len(exception_warning)})")
        tab_data.append(exception_warning)

    if exception_info:
        tab_names.append(f"ℹ️ Прочие ошибки ({len(exception_info)})")
        tab_data.append(exception_info)

    # В конце отображать пройденные проверки
    if passed_items:
        tab_names.append(f"✅ Пройдено ({len(passed_items)})")
        tab_data.append(passed_items)

    if tab_names:
        tabs = st.tabs(tab_names)
        for i, (tab, data) in enumerate(zip(tabs, tab_data)):
            with tab:
                display_items_list(data, tab_names[i].startswith("✅"), report_id=report_id, tab_name=tab_names[i])


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
                        st.error("🔴 Критическая ошибка")
                    elif severity == 'warning':
                        st.warning("🟡 Обычная ошибка")
                    else:
                        st.info("ℹ️ Прочая ошибка")
                elif status == 'passed':
                    st.success("✅ Пройдено")
                else:
                    st.info("ℹ️ Неизвестное состояние")
            solution = item.get('solution', '')
            if solution:
                st.markdown("**💡 Рекомендации по решению:**")
                st.info(solution)


def display_export_page(report_id):
    """Показать страницу экспорта - оптимизированная версия"""
    if st.button("⬅️ Назад"):
        st.session_state.view_mode = "list"
        st.rerun()

    st.markdown(f"### 📥 Экспорт отчёта - {report_id}")

    # Быстрый экспорт
    st.markdown("#### 🚀 Быстрый экспорт")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Экспорт в JSON", width='stretch'):
            export_and_download(report_id, "json", "JSON")

    with col2:
        if st.button("📊 Экспорт в Excel", width='stretch'):
            export_and_download(report_id, "excel", "Excel")

    st.divider()

    # Пользовательские опции экспорта
    st.markdown("#### ⚙️ Настройки экспорта")
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

    if st.button("📥 Начать экспорт", type="primary"):
        export_and_download(report_id, export_format.lower(), export_format,
                           include_passed, include_details)


def export_and_download(report_id, format_type, format_name, include_passed=False, include_details=True):
    """Выполнить экспорт и предоставить файл для скачивания"""
    try:
        from utils.inspection_result import export_report

        success, file_path = export_report(report_id, format_type)

        if success:
            st.success(f"✅ Экспорт в {format_name} выполнен успешно!")

            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                mime_types = {
                    "json": "application/json",
                    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
                st.download_button(
                    label=f"⬇️ Скачать файл {format_name}",
                    data=file_data,
                    file_name=os.path.basename(file_path),
                    mime=mime_types.get(format_type, "application/octet-stream"),
                    type="secondary",
                    width='stretch'
                )
                file_size = len(file_data) / 1024
                st.caption(f"Размер файла: {file_size:.1f} КБ | Путь: {file_path}")
            except Exception as e:
                st.error(f"❌ Ошибка при чтении файла: {str(e)}")
        else:
            st.error(f"❌ Экспорт не удался: {file_path}")
    except Exception as e:
        st.error(f"❌ Ошибка при экспорте: {str(e)}")


def main():
    """Главная функция"""
    initialize_page(
        title="Отчёты проверки",
        icon="📊",
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
            st.error("❌ Отчёт не выбран")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "detail":
        if st.session_state.selected_report_id:
            display_report_detail(st.session_state.selected_report_id)
        else:
            st.error("❌ Отчёт не выбран")
            st.session_state.view_mode = "list"
            st.rerun()
    elif st.session_state.view_mode == "preview":
        if st.session_state.selected_report_id:
            display_report_preview(st.session_state.selected_report_id)
        else:
            st.error("❌ Отчёт не выбран")
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
