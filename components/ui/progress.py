#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection progress display component
"""
import streamlit as st
import time

class InspectionProgress:
    """Inspection progress display class"""

    def __init__(self):
        self.progress_text = st.empty()
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.total_steps = 0
        self.current_step = 0
        self.by_rules = False  # Display progress by number of rules

    def initialize(self, total_steps=3, by_rules=False):
        """Initialize progress component"""
        self.total_steps = total_steps
        self.current_step = 0
        self.by_rules = by_rules
        self.progress_bar.progress(0)

        if by_rules:
            self.status_text.text(f"Preparing to start inspection... (total {total_steps} rules)")
        else:
            self.status_text.text("Preparing to start inspection...")

    def update(self, step_message, step_complete=False, rule_name=None):
        """Update progress"""
        self.progress_text.text(step_message)

        if self.by_rules and rule_name:
            status_msg = f"Executing rule: {rule_name} ({self.current_step + 1}/{self.total_steps})"
            self.status_text.text(status_msg)
        else:
            self.status_text.text(step_message)

        if step_complete:
            self.current_step += 1
            progress = min(1.0, self.current_step / self.total_steps)
            self.progress_bar.progress(progress)

            if self.by_rules:
                status_msg = f"Completed {self.current_step}/{self.total_steps} rules"
                self.status_text.text(status_msg)

    def complete(self, delay=0.5):
        """Complete progress display"""
        self.progress_bar.progress(1.0)
        if self.by_rules:
            self.status_text.text(f"Inspection completed! Total executed {self.total_steps} rules")
        else:
            self.status_text.text("Inspection completed!")
        if delay > 0:
            time.sleep(delay)  # Visual delay for user

    def error(self, message):
        """Display error message"""
        self.status_text.text(f"Error: {message}")

    def warning(self, message):
        """Display warning"""
        self.status_text.text(f"Warning: {message}")
