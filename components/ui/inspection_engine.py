#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единый движок выполнения проверки — устраняет дублирование кода, предоставляет единый интерфейс выполнения проверки
"""
import streamlit as st
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from utils.cluster_config import get_cluster
from utils.inspection_result import InspectionResult
from inspectors.node.node_inspector import NodeInspector
from inspectors.prometheus.prometheus_inspector import PrometheusInspector
from inspectors.opa.opa_inspector import OpaInspector
from inspectors.controller import InspectionController

logger = logging.getLogger(__name__)
from components.ui.progress import InspectionProgress

class InspectionEngine:
    """Единый движок выполнения проверки"""
    def __init__(self):
        self.progress = None

    def execute_inspection(
        self,
        cluster_name: str,
        selected_rules: Dict[str, List[str]] = None,
        inspection_type: str = "immediate",
        show_progress: bool = True,
        show_ui_feedback: bool = True,
        use_gitops: bool = False  # Добавляем параметр для определения источника правил
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Выполнить универсальную проверку

        Args:
            cluster_name: имя кластера
            selected_rules: выбранные правила {"node": [...], "prometheus": [...], "opa": [...]}
            inspection_type: тип проверки ("immediate" или "scheduled")
            show_progress: показывать ли прогресс бар
            show_ui_feedback: показывать ли UI обратную связь
            use_gitops: использовать ли правила GitOps

        Returns:
            (успех, сообщение, результаты)
        """
        self.use_gitops = use_gitops  # Сохраняем информацию об источнике правил

        if show_progress:
            total_rules = 0
            if "node" in selected_rules:
                total_rules += len(selected_rules["node"])
            if "prometheus" in selected_rules:
                total_rules += len(selected_rules["prometheus"])
            if "opa" in selected_rules:
                total_rules += len(selected_rules["opa"])
            self.progress = InspectionProgress()
            self.progress.initialize(total_rules, by_rules=True)

        try:
            if show_progress:
                self.progress.update("Получение конфигурации кластера...")

            cluster_config = get_cluster(cluster_name)
            if not cluster_config:
                error_msg = f"Конфигурация кластера не найдена: {cluster_name}"
                if show_progress:
                    self.progress.error(error_msg)
                return False, error_msg, None

            nodes = cluster_config.get_nodes() if hasattr(cluster_config, 'get_nodes') else []
            prometheus_config = cluster_config.get_prometheus_config() if hasattr(cluster_config, 'get_prometheus_config') else {}
            kubeconfig = cluster_config.get_kubeconfig() if hasattr(cluster_config, 'get_kubeconfig') else ""

            run_node_check = bool(nodes) and (selected_rules and selected_rules.get("node"))
            run_prometheus_check = bool(prometheus_config and prometheus_config.get('enabled', False)) and (selected_rules and selected_rules.get("prometheus"))
            run_opa_check = bool(kubeconfig) and (selected_rules and selected_rules.get("opa"))

            logger.info(f"Проверка типов инспекций - количество узлов: {len(nodes)}, Prometheus включен: {prometheus_config.get('enabled', False) if prometheus_config else False}, kubeconfig: {'есть' if kubeconfig else 'нет'}")
            logger.info(f"Выбранные правила: {selected_rules}")
            logger.info(f"Решение проверок - узлы: {run_node_check}, Prometheus: {run_prometheus_check}, OPA: {run_opa_check}")
            logger.info(f"Режим GitOps: {use_gitops}")

            if not (run_node_check or run_prometheus_check or run_opa_check):
                error_msg = "Нет доступных типов проверки. Проверьте конфигурацию кластера и выбор правил."
                if show_progress:
                    self.progress.error(error_msg)
                return False, error_msg, None

            all_results = {}

            if run_node_check:
                success, result = self._execute_node_inspection(cluster_name, nodes, selected_rules["node"], show_progress)
                if success:
                    all_results['node'] = result
                else:
                    return False, f"Проверка узлов не удалась: {result}", None
            else:
                if show_progress:
                    if self.progress.by_rules and "node" in selected_rules:
                        for rule_id in selected_rules["node"]:
                            self.progress.update(f"Пропущено правило узла: {rule_id} (проверка узлов отключена)", step_complete=True)
                    else:
                        self.progress.update("Пропущена проверка узлов", step_complete=True)

            if run_prometheus_check:
                success, result = self._execute_prometheus_inspection(cluster_name, prometheus_config, selected_rules["prometheus"], show_progress)
                if success:
                    all_results['prometheus'] = result
                else:
                    return False, f"Проверка Prometheus не удалась: {result}", None
            else:
                if show_progress:
                    if self.progress.by_rules and "prometheus" in selected_rules:
                        for rule_id in selected_rules["prometheus"]:
                            self.progress.update(f"Пропущено правило Prometheus: {rule_id} (проверка отключена)", step_complete=True)
                    else:
                        self.progress.update("Пропущена проверка метрик Prometheus", step_complete=True)

            if run_opa_check:
                success, result = self._execute_opa_inspection(cluster_name, kubeconfig, selected_rules["opa"], show_progress)
                if success:
                    all_results['opa'] = result
                else:
                    return False, f"Проверка OPA не удалась: {result}", None
            else:
                if show_progress:
                    if self.progress.by_rules and "opa" in selected_rules:
                        for rule_id in selected_rules["opa"]:
                            self.progress.update(f"Пропущено правило OPA: {rule_id} (проверка отключена)", step_complete=True)
                    else:
                        self.progress.update("Пропущена проверка соответствия OPA", step_complete=True)

            if show_progress:
                self.progress.complete()

            if all_results:
                result_path = self._save_inspection_results(all_results, cluster_name, cluster_config, inspection_type)

                if show_ui_feedback:
                    self._show_inspection_completion_ui(all_results, result_path, cluster_name)

                return True, f"Проверка завершена, результаты сохранены: {result_path}", all_results
            else:
                error_msg = "Не получено результатов проверки."
                if show_progress:
                    self.progress.warning(error_msg)
                return False, error_msg, None
        except Exception as e:
            error_msg = f"Ошибка выполнения проверки: {str(e)}"
            if show_progress:
                self.progress.error(error_msg)
            return False, error_msg, None

    def _execute_node_inspection(self, cluster_name: str, nodes: List[Dict], selected_rules: List[str], show_progress: bool) -> Tuple[bool, Any]:
        """Выполнить проверку узлов"""
        try:
            node_inspector = NodeInspector(nodes, use_gitops=self.use_gitops)

            if show_progress and self.progress.by_rules:
                combined_result = InspectionResult(cluster_name, "node")
                for rule_id in selected_rules:
                    self.progress.update(f"Выполняется правило узла: {rule_id}", rule_name=rule_id)
                    rule_result = node_inspector.run_inspection(cluster_name, [rule_id])
                    if rule_result and hasattr(rule_result, 'items'):
                        for item in rule_result.items:
                            combined_result.add_item(item)
                    self.progress.update(f"Правило узла {rule_id} выполнено", step_complete=True)
                return True, combined_result
            else:
                if show_progress:
                    self.progress.update("Выполнение проверки узлов...")
                result = node_inspector.run_inspection(cluster_name, selected_rules)
                if show_progress:
                    self.progress.update("Проверка узлов завершена", step_complete=True)
                return True, result
        except Exception as e:
            if show_progress:
                self.progress.error(f"Ошибка проверки узлов: {e}")
            return False, str(e)

    def _execute_prometheus_inspection(self, cluster_name: str, prometheus_config: Dict, selected_rules: List[str], show_progress: bool) -> Tuple[bool, Any]:
        """Выполнить проверку Prometheus"""
        try:
            if prometheus_config and prometheus_config.get("enabled", False):
                prometheus_inspector = PrometheusInspector(prometheus_config, use_gitops=self.use_gitops)
                if show_progress and self.progress.by_rules:
                    combined_result = InspectionResult(cluster_name, "prometheus")
                    for rule_id in selected_rules:
                        self.progress.update(f"Выполняется правило Prometheus: {rule_id}", rule_name=rule_id)
                        rule_result = prometheus_inspector.run_inspection(cluster_name, [rule_id])
                        if rule_result and hasattr(rule_result, 'items'):
                            for item in rule_result.items:
                                combined_result.add_item(item)
                        self.progress.update(f"Правило Prometheus {rule_id} выполнено", step_complete=True)
                    return True, combined_result
                else:
                    if show_progress:
                        self.progress.update("Выполнение проверки метрик Prometheus...")
                    result = prometheus_inspector.run_inspection(cluster_name, selected_rules)
                    if show_progress:
                        self.progress.update("Проверка метрик Prometheus завершена", step_complete=True)
                    return True, result
            else:
                if show_progress:
                    if self.progress.by_rules:
                        for rule_id in selected_rules:
                            self.progress.update(f"Пропущено правило Prometheus: {rule_id} (нет конфигурации)", step_complete=True)
                    else:
                        self.progress.update("Пропущена проверка Prometheus (нет конфигурации)", step_complete=True)
                return True, None
        except Exception as e:
            if show_progress:
                self.progress.error(f"Ошибка проверки метрик Prometheus: {e}")
            return False, str(e)

    def _execute_opa_inspection(self, cluster_name: str, kubeconfig: str, selected_rules: List[str], show_progress: bool) -> Tuple[bool, Any]:
        """Выполнить проверку OPA"""
        try:
            if kubeconfig:
                opa_config = {'kubeconfig': kubeconfig, 'opa_path': 'opa'}
                opa_inspector = OpaInspector(opa_config, use_gitops=self.use_gitops)
                if show_progress and self.progress.by_rules:
                    combined_result = InspectionResult(cluster_name, "opa")
                    for rule_id in selected_rules:
                        self.progress.update(f"Выполняется правило OPA: {rule_id}", rule_name=rule_id)
                        rule_result = opa_inspector.run_inspection(cluster_name, [rule_id])
                        if rule_result and hasattr(rule_result, 'items'):
                            for item in rule_result.items:
                                combined_result.add_item(item)
                        self.progress.update(f"Правило OPA {rule_id} выполнено", step_complete=True)
                    return True, combined_result
                else:
                    if show_progress:
                        self.progress.update("Выполнение проверки соответствия OPA...")
                    result = opa_inspector.run_inspection(cluster_name, selected_rules)
                    if show_progress:
                        self.progress.update("Проверка соответствия OPA завершена", step_complete=True)
                    return True, result
            else:
                if show_progress:
                    if self.progress.by_rules:
                        for rule_id in selected_rules:
                            self.progress.update(f"Пропущено правило OPA: {rule_id} (нет конфигурации)", step_complete=True)
                    else:
                        self.progress.update("Пропущена проверка соответствия OPA (нет конфигурации)", step_complete=True)
                return True, None
        except Exception as e:
            if show_progress:
                self.progress.error(f"Ошибка проверки соответствия OPA: {e}")
            return False, str(e)

    def _save_inspection_results(self, all_results: Dict, cluster_name: str, cluster_config: Any, inspection_type: str) -> str:
        """Сохранить результаты проверки"""
        try:
            if hasattr(cluster_config, 'get_dict'):
                config_dict = cluster_config.get_dict()
            else:
                config_dict = {
                    'nodes': cluster_config.get_nodes() if hasattr(cluster_config, 'get_nodes') else [],
                    'prometheus': cluster_config.get_prometheus_config() if hasattr(cluster_config, 'get_prometheus_config') else {},
                    'opa': {'kubeconfig': cluster_config.get_kubeconfig() if hasattr(cluster_config, 'get_kubeconfig') else ''}
                }
        except Exception:
            config_dict = {'nodes': [], 'prometheus': {}, 'opa': {'kubeconfig': ''}}

        controller = InspectionController(config_dict, use_gitops=self.use_gitops)
        return controller.save_inspection_result(all_results, cluster_name, inspection_type)

    def _show_inspection_completion_ui(self, all_results: Dict, result_path: str, cluster_name: str):
        """Показать UI обратной связи после завершения проверки"""
        # Определяем источник правил для отображения
        rules_source = "GitOps" if self.use_gitops else "Локальные"

        st.success(f"Проверка завершена с использованием {rules_source} правил!")

        total_items = sum(len(result.items) if hasattr(result, 'items') else 0 for result in all_results.values() if result)
        passed_count = 0
        exception_count = 0

        for result in all_results.values():
            if result and hasattr(result, 'items'):
                passed_count += len([item for item in result.items if item.get('status') == 'passed'])
                exception_count += len([item for item in result.items if item.get('status') != 'passed'])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего проверок", total_items)
        with col2:
            st.metric("Пройдено", passed_count)
        with col3:
            st.metric("Ошибок", exception_count)

        st.session_state.last_result_path = result_path
        st.session_state.last_cluster_name = cluster_name

        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            st.session_state.last_result_id = result_data.get('result_id')
        except Exception:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.session_state.last_result_id = f"immediate_{timestamp}"

        col1, col2 = st.columns(2)

        with col1:
            result_id = st.session_state.get("last_result_id")
            if result_id:
                st.session_state.selected_report_id = result_id
                st.session_state.view_mode = "detail"
            st.success("Проверка завершена! Отчёт готов к просмотру.")
            st.info("Пожалуйста, перейдите на страницу «Отчёты проверки» в левой навигации для просмотра деталей.")

        with col2:
            if st.button("Повторить проверку", width='stretch'):
                st.rerun()


inspection_engine = InspectionEngine()

def execute_inspection_unified(cluster_name: str, selected_rules: Dict[str, List[str]] = None,
                             inspection_type: str = "immediate", show_progress: bool = True,
                             show_ui_feedback: bool = True, use_gitops: bool = False) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Единый интерфейс запуска проверки для всех компонентов"""
    return inspection_engine.execute_inspection(
        cluster_name, selected_rules, inspection_type, show_progress, show_ui_feedback, use_gitops
    )

def execute_inspection_task(task, show_progress=True):
    """Совместимость старого интерфейса для плановых задач"""
    selected_rules = {}
    if hasattr(task, 'rules') and task.rules:
        for rule_type in ['node', 'prometheus', 'opa']:
            if rule_type in task.rules and task.rules[rule_type].get("enabled", False):
                selected_rules[rule_type] = task.rules[rule_type].get("rules", [])

    # Определяем, использовать ли GitOps для плановых задач
    from utils.rule_manager import RuleManager
    use_gitops = RuleManager.should_use_gitops()

    return execute_inspection_unified(
        cluster_name=task.cluster,
        selected_rules=selected_rules,
        inspection_type="scheduled",
        show_progress=show_progress,
        show_ui_feedback=False,
        use_gitops=use_gitops
    )
