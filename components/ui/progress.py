#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент отображения прогресса проверки
"""
import streamlit as st
import time

class InspectionProgress:
    """Класс отображения прогресса проверки"""

    def __init__(self):
        self.progress_text = st.empty()
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.total_steps = 0
        self.current_step = 0
        self.by_rules = False  # Отображать прогресс по количеству правил

    def initialize(self, total_steps=3, by_rules=False):
        """Инициализация компонента прогресса"""
        self.total_steps = total_steps
        self.current_step = 0
        self.by_rules = by_rules
        self.progress_bar.progress(0)

        if by_rules:
            self.status_text.text(f"Готовимся начать проверку... (всего {total_steps} правил)")
        else:
            self.status_text.text("Готовимся начать проверку...")

    def update(self, step_message, step_complete=False, rule_name=None):
        """Обновить прогресс"""
        self.progress_text.text(step_message)

        if self.by_rules and rule_name:
            status_msg = f"Выполняется правило: {rule_name} ({self.current_step + 1}/{self.total_steps})"
            self.status_text.text(status_msg)
        else:
            self.status_text.text(step_message)

        if step_complete:
            self.current_step += 1
            progress = min(1.0, self.current_step / self.total_steps)
            self.progress_bar.progress(progress)

            if self.by_rules:
                status_msg = f"Завершено {self.current_step}/{self.total_steps} правил"
                self.status_text.text(status_msg)

    def complete(self, delay=0.5):
        """Завершить отображение прогресса"""
        self.progress_bar.progress(1.0)
        if self.by_rules:
            self.status_text.text(f"Проверка завершена! Всего выполнено {self.total_steps} правил")
        else:
            self.status_text.text("Проверка завершена!")
        if delay > 0:
            time.sleep(delay)  # Визуальная задержка для пользователя

    def error(self, message):
        """Отобразить сообщение об ошибке"""
        self.status_text.text(f"Ошибка: {message}")

    def warning(self, message):
        """Отобразить предупреждение"""
        self.status_text.text(f"Предупреждение: {message}")
