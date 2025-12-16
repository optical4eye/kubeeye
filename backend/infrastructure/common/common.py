#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common utilities for backend API
"""

import sys
from pathlib import Path


def create_status_badge(status, text=None):
    """
    Create status badge

    Args:
        status: Status type ('success', 'warning', 'error', 'info')
        text: Display text, if None then use status itself

    Returns:
        str: HTML code for badge
    """
    if text is None:
        text = status.title()

    colors = {
        "success": ("#E7F9ED", "#1E8E3E"),  # Light green background, dark green text
        "warning": ("#FEF7E0", "#E67700"),  # Light yellow background, orange text
        "error": ("#FFE5E5", "#D93025"),  # Light red background, red text
        "info": ("#E8F0FE", "#1A73E8"),  # Light blue background, blue text
    }

    bg_color, text_color = colors.get(status.lower(), colors["info"])

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
