#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes cluster inspection execution page
"""


# Import necessary libraries
import streamlit as st
import sys
from pathlib import Path


# Page parameter setup - must be the first Streamlit command
st.set_page_config(
    page_title="Cluster inspection - kubeeye",
    layout="wide"
)


# Add project root directory to Python paths
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Import module with common utilities
from utils.common import initialize_page
# Import component modules
from components.immediate_scan import render_immediate_scan_tab
from components.scheduled_scan import render_scheduled_scan_tab
from components.rule_management import render_rule_management_tab


# Page initialization
initialize_page(
    title="Cluster inspection",
    page_title="Cluster inspection center",
    page_subtitle="Execute immediate or scheduled inspection, manage inspection rules"
)


# Create three tabs
tab1, tab2, tab3 = st.tabs(["Immediate inspection", "Scheduled inspection", "Rule management"])


# Render immediate inspection tab
with tab1:
    render_immediate_scan_tab()


# Render scheduled inspection tab
with tab2:
    render_scheduled_scan_tab()


# Render rule management tab
with tab3:
    render_rule_management_tab()
