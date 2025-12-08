#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common components and helper functions - reducing duplicate code between pages
"""

import sys
from pathlib import Path

# Import project modules
from utils.navbar import set_app_styles, show_app_logo, create_sidebar_header, create_page_header

# Global variable, ensure initialization only once
_background_services_initialized = False

def _initialize_background_services():
    """
    Initialize background services (scheduled tasks, data cleanup, etc.)
    Use global variable to ensure initialization only once
    """
    global _background_services_initialized

    if _background_services_initialized:
        return

    try:
        # Import and start data cleanup module

        # Import and start task scheduler

        _background_services_initialized = True

    except ImportError as e:
        # If module does not exist, log error but do not affect page loading
        pass
    except Exception as e:
        # Other errors also do not affect page loading
        pass

def initialize_page(title, icon="", sidebar_name="", page_title="", page_subtitle="", page_icon="", breadcrumbs=None):
    """
    Initialize page settings, including styles and navigation panel
    Note: this function assumes that st.set_page_config() has already been called before calling this function

    Args:
        title: Page title
        icon: Page icon
        sidebar_name: Sidebar name
        page_title: Page title (if different from title)
        page_subtitle: Page subtitle
        page_icon: Page icon (if different from icon)
        breadcrumbs: List of breadcrumbs [{"title": "Home", "path": "app.py"}, ...]

    Returns:
        None
    """
    # Initialize background services (executed only on first call)
    _initialize_background_services()

    # No longer call st.set_page_config() - should be called before using this function

    # Ensure project root directory is in Python path
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    # Set application styles
    set_app_styles()

    # Show application logo
    show_app_logo()

    # Create sidebar and page header
    create_sidebar_header(sidebar_name or title)
    create_page_header(page_title or title, page_subtitle, icon=page_icon or icon, breadcrumbs=breadcrumbs)

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
        'success': ('#E7F9ED', '#1E8E3E'),  # Light green background, dark green text
        'warning': ('#FEF7E0', '#E67700'),  # Light yellow background, orange text
        'error': ('#FFE5E5', '#D93025'),    # Light red background, red text
        'info': ('#E8F0FE', '#1A73E8')      # Light blue background, blue text
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
