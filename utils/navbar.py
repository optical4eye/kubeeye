#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент навигационной панели — используется для создания единообразного навигационного меню на всех страницах
"""

import streamlit as st
from pathlib import Path
from utils.version import VERSION

def set_app_styles():
    """
    Установить базовые стили приложения

    Возвращает:
        None
    """
    st.markdown("""
    <style>
    /* Скрыть стандартный заголовок страницы и футер */
    .main .block-container h1:first-child { display: none; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* Улучшение общего интерфейса и отступов */
    .main .block-container { padding-top: 1.5rem; }

    /* Основные стили боковой панели */
    [data-testid="stSidebar"] {
        background-color: #948979;
        border-right: 1px solid rgba(0,0,0,0.05);
        resize: none !important;
        min-width: 244px !important;
        max-width: 244px !important;
        width: 244px !important;
    }

    /* Отключение возможности перетаскивания и изменения размера боковой панели */
    [data-testid="stSidebar"] .css-1d391kg,
    [data-testid="stSidebar"] .css-1y4p8pa,
    [data-testid="stSidebar"] .css-1cypcdb {
        resize: none !important;
        min-width: 244px !important;
        max-width: 244px !important;
        width: 244px !important;
    }

    /* Скрытие перетаскивающих рукояток боковой панели */
    [data-testid="stSidebar"] .css-1d391kg::after,
    [data-testid="stSidebar"] .css-1y4p8pa::after,
    [data-testid="stSidebar"] .css-1cypcdb::after {
        display: none !important;
    }

    /* Отключение изменения размера мышью у правого края боковой панели при наведении */
    [data-testid="stSidebar"]:hover {
        cursor: default !important;
    }

    [data-testid="stSidebar"] * {
        resize: none !important;
    }

    /* Стили заголовков */
    h1, h2, h3 {
        color: #333;
        font-weight: 600;
    }

    /* Улучшение стилей кнопок */
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        margin-bottom: 0.5rem !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }

    /* Улучшение стилей ссылок */
    [data-testid="stSidebar"] a {
        transition: color 0.2s ease !important;
    }

    [data-testid="stSidebar"] a:hover {
        color: #007acc !important;
    }
    </style>
    """, unsafe_allow_html=True)

def show_app_logo():
    """
    Отобразить логотип приложения — эту функцию следует вызывать после st.set_page_config

    Возвращает:
        None
    """
    try:
        root_dir = Path(__file__).resolve().parents[1]
        logo_path = str(root_dir / "static/kubeeye-logo.svg")
        icon_path = str(root_dir / "static/kubeeye.ico")

        st.logo(
            image=logo_path,
            size="large",
            icon_image=icon_path,
            link="https://github.com/kubesphere/kubeeye"
        )
        st.markdown('<div style="height: 10px"></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Ошибка загрузки логотипа: {str(e)}")
        st.title("KubeEye - инструмент проверки кластера Kubernetes")

def create_sidebar_header(active_page="Главная"):
    """
    Создать навигационное меню в верхней части боковой панели с информацией об авторских правах внизу

    Args:
        active_page: название текущей активной страницы

    Возвращает:
        None
    """
    menu_items = [
        {"title": "Главная", "path": "app.py", "label": "Главная", "icon": "🏠"},
        {"title": "Инфо о кластере", "path": "pages/1_cluster_info.py", "label": "Информация", "icon": "🔗"},
        {"title": "Проверка кластера", "path": "pages/2_cluster_inspect.py", "label": "Проверка", "icon": "🔍"},
        {"title": "Отчёты проверки", "path": "pages/3_inspect_report.py", "label": "Отчёты", "icon": "📊"},
    ]

    with st.sidebar:
        st.markdown("###")

        for item in menu_items:
            is_active = active_page == item["label"]
            button_type = "primary" if is_active else "secondary"

            if st.button(f"{item['icon']} {item['title']}",
                         type=button_type,
                         use_container_width=True,
                         key=f"nav_{item['label']}"):
                try:
                    st.switch_page(item["path"])
                except Exception as e:
                    st.error(f"Ошибка перехода на страницу: {str(e)}")
                    st.info(f"Пытался перейти на: {item['path']}")

        st.markdown("""
        <style>
        .sidebar-footer {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            width: 244px !important;
            background-color: #948979 !important;
            border-top: 1px solid rgba(0, 0, 0, 0.15) !important;
            padding: 0.8rem 1rem !important;
            text-align: center !important;
            font-size: 0.7rem !important;
            color: #ffffff !important;
            line-height: 1.4 !important;
            z-index: 9999 !important;
            transition: all 0.3s ease !important;
        }
        .sidebar-footer a {
            color: #ffffff !important;
            text-decoration: none !important;
            font-weight: 500 !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.3) !important;
        }
        .sidebar-footer a:hover {
            color: #f0f0f0 !important;
            border-bottom-color: rgba(255, 255, 255, 0.6) !important;
        }
        [data-testid="stSidebar"][aria-expanded="false"] ~ * .sidebar-footer,
        [data-testid="stSidebar"].st-emotion-cache-1d391kg ~ * .sidebar-footer {
            transform: translateX(-100%) !important;
            opacity: 0 !important;
        }
        @media (max-width: 768px) {
            .sidebar-footer {
                display: none !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="sidebar-footer">
            <div style="margin-bottom: 4px; font-weight: 500; color: #ffffff;">© 2025 KubeEye v{VERSION}</div>
            <div><a href="https://kubesphere.io" target="_blank">KubeSphere</a></div>
        </div>
        """, unsafe_allow_html=True)

def create_page_header(title, subtitle="", icon=""):
    """
    Создать заголовок страницы

    Args:
        title: заголовок страницы
        subtitle: подзаголовок страницы
        icon: иконка (необязательно)

    Возвращает:
        None
    """
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <h2 style="color: #333; font-weight: 600; margin-bottom: 0.25rem;">
            {icon} {title}
        </h2>
        <p style="color: #666; font-size: 1rem; margin-top: 0;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="height: 1px; border: none; background: #eaeaea; margin: 1rem 0;" />', unsafe_allow_html=True)
