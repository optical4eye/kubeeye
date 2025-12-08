#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Navigation bar component - used to create a consistent navigation menu on all pages
"""

import streamlit as st
from pathlib import Path
from utils.version import VERSION

def set_app_styles():
    """
    Set basic application styles (dark theme)

    Returns:
        None
    """
    # Dark theme by default
    base_bg = "#1e1e1e"
    base_color = "#ffffff"
    sidebar_bg = "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%)"
    card_bg = "#2d2d2d"

    # CSS styles with variables
    css_styles = f"""
    <style>
    /* Hide standard page title and footer */
    .main .block-container h1:first-child {{ display: none; }}
    footer {{ visibility: hidden; }}
    #MainMenu {{ visibility: hidden; }}

    /* Improvement of general interface and indents */
    .main .block-container {{ padding-top: 1.5rem; }}

    /* Main sidebar styles */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg};
        border-right: 1px solid rgba(0,0,0,0.05);
        resize: none !important;
        min-width: 244px !important;
        max-width: 244px !important;
        width: 244px !important;
    }}

    /* Dark theme */
    .main {{
        background-color: {base_bg};
        color: {base_color};
    }}

    .stCard {{
        background-color: {card_bg};
    }}

    /* Headers */
    h1, h2, h3 {{
        color: {base_color};
    }}

    /* Dark theme for footer */
    .sidebar-footer {{
        background: {sidebar_bg} !important;
        color: {base_color} !important;
    }}


    [data-testid="stSidebar"] .css-1d391kg,
    [data-testid="stSidebar"] .css-1y4p8pa,
    [data-testid="stSidebar"] .css-1cypcdb {{
        resize: none !important;
        min-width: 244px !important;
        max-width: 244px !important;
        width: 244px !important;
    }}

    [data-testid="stSidebar"] .css-1d391kg::after,
    [data-testid="stSidebar"] .css-1y4p8pa::after,
    [data-testid="stSidebar"] .css-1cypcdb::after {{
        display: none !important;
    }}

    [data-testid="stSidebar"]:hover {{
        cursor: default !important;
    }}

    [data-testid="stSidebar"] * {{
        resize: none !important;
    }}

    h1, h2, h3 {{
        color: {base_color};
        font-weight: 600;
    }}

    [data-testid="stSidebar"] .stButton > button {{
        width: 100% !important;
        margin-bottom: 0.5rem !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }}

    [data-testid="stSidebar"] a {{
        transition: color 0.2s ease !important;
    }}

    [data-testid="stSidebar"] a:hover {{
        color: #007acc !important;
    }}

    .fade-in {{
        animation: fadeIn 0.3s ease-in;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .slide-in {{
        animation: slideIn 0.4s ease-out;
    }}

    @keyframes slideIn {{
        from {{ transform: translateX(-20px); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}

    .stButton > button {{
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }}

    .stButton > button:active {{
        transform: translateY(0) !important;
        transition: all 0.1s !important;
    }}

    [data-testid="stExpander"] {{
        transition: all 0.2s ease !important;
    }}

    [data-testid="stExpander"]:hover {{
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    }}

    .metric-animation {{
        animation: metricPulse 0.6s ease-out;
    }}

    @keyframes metricPulse {{
        0% {{ transform: scale(0.95); opacity: 0; }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(1); opacity: 1; }}
    }}

    .loading-spinner {{
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: #ffffff;
        animation: spin 1s ease-in-out infinite;
        margin-right: 8px;
    }}

    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}

    .loading-dots {{
        display: inline-block;
    }}

    .loading-dots::after {{
        content: '';
        animation: dots 1.5s infinite;
    }}

    @keyframes dots {{
        0%, 20% {{ content: ''; }}
        40% {{ content: '.'; }}
        60% {{ content: '..'; }}
        80%, 100% {{ content: '...'; }}
    }}

    .toast-container {{
        position: fixed !important;
        top: 20px !important;
        right: 20px !important;
        z-index: 10000 !important;
        max-width: 400px !important;
    }}

    .toast {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
        color: white !important;
        padding: 16px 20px !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
        border-left: 4px solid #326CE5 !important;
        animation: toastSlideIn 0.3s ease-out !important;
        backdrop-filter: blur(10px) !important;
    }}

    .toast.success {{
        border-left-color: #00D4AA !important;
    }}

    .toast.error {{
        border-left-color: #FF6B6B !important;
    }}

    .toast.warning {{
        border-left-color: #FFC107 !important;
    }}

    .toast.info {{
        border-left-color: #17a2b8 !important;
    }}

    @keyframes toastSlideIn {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}

    .toast.fade-out {{
        animation: toastFadeOut 0.3s ease-in forwards !important;
    }}

    @keyframes toastFadeOut {{
        to {{
            transform: translateX(100%);
            opacity: 0;
        }}
    }}

    .pulse {{
        animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(50, 108, 229, 0.7); }}
        70% {{ box-shadow: 0 0 0 10px rgba(50, 108, 229, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(50, 108, 229, 0); }}
    }}

    * {{
        transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease !important;
    }}
    </style>
    """

    st.markdown(css_styles, unsafe_allow_html=True)

    st.markdown(f"""
    <script>

    // Toast notification system
    window.showToast = function(message, type = 'info', duration = 4000) {{
        // Create container if it doesn't exist
        let container = document.querySelector('.toast-container');
        if (!container) {{
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }}

        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast ${{type}} fade-in`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 18px;">
                    ${{type === 'success' ? 'OK' : type === 'error' ? 'ERR' : type === 'warning' ? 'WARN' : 'INFO'}}
                </div>
                <div style="flex: 1;">${{message}}</div>
                <button onclick="this.parentElement.parentElement.remove()"
                        style="background: none; border: none; color: white; cursor: pointer; font-size: 16px;">×</button>
            </div>
        `;

        container.appendChild(toast);

        // Automatic removal
        setTimeout(() => {{
            toast.classList.add('fade-out');
            setTimeout(() => {{
                if (toast.parentElement) {{
                    toast.remove();
                }}
            }}, 300);
        }}, duration);

        return toast;
    }};

    // Override Streamlit success/error/info functions to use toast
    const originalSuccess = window.parent.streamlitSuccess || (() => {{}});
    const originalError = window.parent.streamlitError || (() => {{}});
    const originalInfo = window.parent.streamlitInfo || (() => {{}});

    // Add animations to metrics on load
    function animateMetrics() {{
        const metrics = document.querySelectorAll('[data-testid="stMetricValue"]');
        metrics.forEach((metric, index) => {{
            metric.style.animationDelay = `${{index * 0.1}}s`;
            metric.classList.add('metric-animation');
        }});
    }}

    // Call metric animations on page load
    setTimeout(animateMetrics, 100);

    // Add fade-in to all main elements
    function addFadeInAnimations() {{
        const elements = document.querySelectorAll('h1, h2, h3, .stDataFrame, .stColumns, [data-testid="stExpander"]');
        elements.forEach((el, index) => {{
            el.style.animationDelay = `${{index * 0.05}}s`;
            el.classList.add('fade-in');
        }});
    }}

    setTimeout(addFadeInAnimations, 200);

    // Enhanced loading states
    window.showLoading = function(element, text = 'Loading...') {{
        if (typeof element === 'string') {{
            element = document.querySelector(element);
        }}
        if (!element) return;

        element.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; padding: 20px;">
                <div class="loading-spinner"></div>
                <span>${{text}}</span>
            </div>
        `;
    }};

    window.hideLoading = function(element) {{
        if (typeof element === 'string') {{
            element = document.querySelector(element);
        }}
        if (!element) return;

        // Restore original content or just clear
        element.innerHTML = '';
    }};
    </script>
    """, unsafe_allow_html=True)

def show_app_logo():
    """
    Display application logo - this function should be called after st.set_page_config

    Returns:
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
        st.warning(f"Error loading logo: {str(e)}")
        st.title("KubeEye - Kubernetes cluster inspection tool")

def create_sidebar_header(active_page="Home"):
    """
    Create navigation menu at the top of the sidebar with copyright information at the bottom

    Args:
        active_page: name of the current active page

    Returns:
        None
    """
    menu_items = [
        {"title": "Home", "path": "app.py", "label": "Home", "icon": ""},
        {"title": "Cluster Info", "path": "pages/1_cluster_info.py", "label": "Information", "icon": ""},
        {"title": "Cluster Inspection", "path": "pages/2_cluster_inspect.py", "label": "Inspection", "icon": ""},
        {"title": "Inspection Reports", "path": "pages/3_inspect_report.py", "label": "Reports", "icon": ""},
    ]

    with st.sidebar:
        st.markdown("###")

        for item in menu_items:
            is_active = active_page == item["label"]
            button_type = "primary" if is_active else "secondary"

            if st.button(item['title'],
                           type=button_type,
                           width='stretch',
                           key=f"nav_{item['label']}"):
                try:
                    st.switch_page(item["path"])
                except Exception as e:
                    st.error(f"Error navigating to page: {str(e)}")
                    st.info(f"Tried to navigate to: {item['path']}")

        st.markdown("""
        <style>
        .sidebar-footer {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            width: 244px !important;
            background-color: {sidebar_bg} !important;
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


def create_page_header(title, subtitle="", icon="", breadcrumbs=None):
    """
    Create page header with breadcrumbs

    Args:
        title: page title
        subtitle: page subtitle
        icon: icon (optional)
        breadcrumbs: list of dictionaries [{"title": "Home", "path": "app.py"}, ...]

    Returns:
        None
    """
    # Colors for dark theme
    base_color = "#ffffff"
    subtitle_color = "#cccccc"
    # Breadcrumbs
    if breadcrumbs:
        breadcrumb_html = '<nav aria-label="breadcrumb"><ol class="breadcrumb" style="background: none; padding: 0; margin-bottom: 1rem;">'
        for i, crumb in enumerate(breadcrumbs):
            if i < len(breadcrumbs) - 1:
                breadcrumb_html += f'<li class="breadcrumb-item"><a href="#" onclick="window.location.href=\'{crumb.get("path", "#")}\'">{crumb["title"]}</a></li>'
            else:
                breadcrumb_html += f'<li class="breadcrumb-item active" aria-current="page">{crumb["title"]}</li>'
        breadcrumb_html += '</ol></nav>'
        st.markdown(breadcrumb_html, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <h2 style="color: {base_color}; font-weight: 600; margin-bottom: 0.25rem;">
            {icon} {title}
        </h2>
        <p style="color: {subtitle_color}; font-size: 1rem; margin-top: 0;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="height: 1px; border: none; background: #eaeaea; margin: 1rem 0;" />', unsafe_allow_html=True)
