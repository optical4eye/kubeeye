#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент выбора инспектора
"""
import streamlit as st

def select_inspectors(nodes, prometheus_config, kubeconfig):
    """Определить доступные типы инспекторов"""
    run_node_check = bool(nodes)
    run_prometheus_check = bool(prometheus_config and prometheus_config.get('enabled', False))
    run_opa_check = bool(kubeconfig)

    st.session_state.run_node_check = run_node_check
    st.session_state.run_prometheus_check = run_prometheus_check
    st.session_state.run_opa_check = run_opa_check

    return run_node_check, run_prometheus_check, run_opa_check
