#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Страница исполнения проверки кластера Kubernetes
"""


# Импорт необходимых библиотек
import streamlit as st
import sys
from pathlib import Path


# Настройка параметров страницы — должна быть первой командой Streamlit
st.set_page_config(
    page_title="Проверка кластера - kubeeye",
    layout="wide"
)


# Добавление корневой директории проекта в пути Python
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Импорт модуля с общими утилитами
from utils.common import initialize_page
# Импорт модулей компонентов
from components.immediate_scan import render_immediate_scan_tab
from components.scheduled_scan import render_scheduled_scan_tab
from components.rule_management import render_rule_management_tab


# Инициализация страницы
initialize_page(
    title="Проверка кластера",
    page_title="Центр проверки кластера",
    page_subtitle="Выполнение немедленной или плановой проверки, управление правилами проверки"
)


# Создание трёх вкладок
tab1, tab2, tab3 = st.tabs(["Немедленная проверка", "Плановая проверка", "Управление правилами"])


# Отрисовка вкладки немедленной проверки
with tab1:
    render_immediate_scan_tab()


# Отрисовка вкладки плановой проверки
with tab2:
    render_scheduled_scan_tab()


# Отрисовка вкладки управления правилами
with tab3:
    render_rule_management_tab()
