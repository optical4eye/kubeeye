#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Общие компоненты и вспомогательные функции - уменьшение повторяющегося кода между страницами
"""

import streamlit as st
import sys
from pathlib import Path

# Импорт модулей проекта
from utils.navbar import set_app_styles, show_app_logo, create_sidebar_header, create_page_header

# Глобальная переменная, обеспечение инициализации только один раз
_background_services_initialized = False

def _initialize_background_services():
    """
    Инициализировать фоновые службы (запланированные задачи, очистка данных и т.д.)
    Использовать глобальную переменную для обеспечения инициализации только один раз
    """
    global _background_services_initialized

    if _background_services_initialized:
        return

    try:
        # Импорт и запуск модуля очистки данных
        import utils.data_cleanup

        # Импорт и запуск планировщика задач
        import utils.schedule_manager

        _background_services_initialized = True

    except ImportError as e:
        # Если модуль не существует, записать ошибку но не влиять на загрузку страницы
        pass
    except Exception as e:
        # Другие ошибки также не влияют на загрузку страницы
        pass

def initialize_page(title, icon="", sidebar_name="", page_title="", page_subtitle="", page_icon="", breadcrumbs=None):
    """
    Инициализировать настройки страницы, включая стили и навигационную панель
    Примечание: эта функция предполагает, что st.set_page_config() уже был вызван перед вызовом этой функции

    Args:
        title: Заголовок страницы
        icon: Иконка страницы
        sidebar_name: Название боковой панели
        page_title: Заголовок страницы (если отличается от title)
        page_subtitle: Подзаголовок страницы
        page_icon: Иконка страницы (если отличается от icon)
        breadcrumbs: Список breadcrumbs [{"title": "Главная", "path": "app.py"}, ...]

    Returns:
        None
    """
    # Инициализировать фоновые службы (выполняется только при первом вызове)
    _initialize_background_services()

    # Больше не вызывать st.set_page_config() - должен быть вызван перед использованием этой функции

    # Обеспечить, что корневой каталог проекта находится в пути Python
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    # Установить стили приложения
    set_app_styles()

    # Показать логотип приложения
    show_app_logo()

    # Создать боковую панель и заголовок страницы
    create_sidebar_header(sidebar_name or title)
    create_page_header(page_title or title, page_subtitle, icon=page_icon or icon, breadcrumbs=breadcrumbs)

def create_status_badge(status, text=None):
    """
    Создать значок статуса

    Args:
        status: Тип статуса ('success', 'warning', 'error', 'info')
        text: Отображаемый текст, если None то использовать сам статус

    Returns:
        str: HTML код значка
    """
    if text is None:
        text = status.title()

    colors = {
        'success': ('#E7F9ED', '#1E8E3E'),  # Светло-зеленый фон, темно-зеленый текст
        'warning': ('#FEF7E0', '#E67700'),  # Светло-желтый фон, оранжевый текст
        'error': ('#FFE5E5', '#D93025'),    # Светло-красный фон, красный текст
        'info': ('#E8F0FE', '#1A73E8')      # Светло-синий фон, синий текст
    }

    bg_color, text_color = colors.get(status.lower(), colors['info'])

    return f"""
    <span style="
        background-color: {bg_color};
        color: {text_color};
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
    ">{text}</span>
    """
