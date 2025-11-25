#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент отображения информации о кластере
"""
import streamlit as st
from utils.cluster_config import get_cluster

def display_cluster_info(cluster_name):
    """Отобразить основную информацию о кластере"""
    cluster_config = get_cluster(cluster_name)
    if not cluster_config:
        st.error(f"Не удалось загрузить конфигурацию кластера: {cluster_name}")
        return None, None, None

    with st.expander("Основная информация о кластере", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Название кластера:** {cluster_name}")
            description = getattr(cluster_config, 'description', '') or cluster_config.config.get('description', 'Описание отсутствует')
            st.markdown(f"**Описание кластера:** {description}")
            nodes = cluster_config.get_nodes()
            st.markdown(f"**Количество узлов:** {len(nodes)}")

        with col2:
            prometheus_config = cluster_config.get_prometheus_config() or {}
            if prometheus_config and prometheus_config.get('enabled', False):
                st.markdown(f"**Адрес Prometheus:** {prometheus_config.get('url', 'N/A')}")
            else:
                st.markdown("**Prometheus:** не настроен")

            kubeconfig = cluster_config.get_kubeconfig()
            if kubeconfig:
                st.markdown("**Kubeconfig:** настроен")
            else:
                st.markdown("**Kubeconfig:** не настроен")

    return cluster_config, cluster_config.get_nodes(), cluster_config.get_prometheus_config() or {}
