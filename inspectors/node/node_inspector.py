#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инспектор узлов с централизованным управлением ошибками SSH соединений
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple, Union

from inspectors.base_inspector import BaseInspector
from utils.inspection_result import InspectionResult
from utils.rule_loader import Rule
from utils.node_connection import NodeConnection, test_node_connection
from utils.command_security import CommandSecurityChecker, RiskLevel
from utils.result_formatter import ResultFormatter

# Настройка логирования
logger = logging.getLogger(__name__)

class SSHConnectionErrorManager:
    """
    Централизованный менеджер ошибок SSH соединений
    Гарантирует, что каждая ошибка для хоста отображается только один раз
    """

    def __init__(self):
        self._errors_registry = {}  # {node_key: error_data}
        self._result_formatter = ResultFormatter()

    def reset_for_inspection(self):
        """Сброс реестра ошибок перед новой проверкой"""
        self._errors_registry = {}
        logger.info("🔄 Реестр ошибок SSH соединений сброшен для новой проверки")

    def register_connection_error(self, node: Dict, error_message: str) -> str:
        """
        Регистрация ошибки соединения для узла
        """
        node_key = self._get_node_key(node)

        # Если ошибка уже зарегистрирована, не регистрируем повторно
        if node_key in self._errors_registry:
            return node_key

        # Регистрируем новую ошибку
        self._errors_registry[node_key] = {
            'node': node.copy(),
            'error_message': error_message,
            'timestamp': time.time(),
            'formatted_result': None
        }

        logger.warning(f"🚫 Зарегистрирована ошибка SSH для узла {node_key}: {error_message}")
        return node_key

    def has_connection_error(self, node: Dict) -> bool:
        """Проверка наличия ошибки соединения для узла"""
        node_key = self._get_node_key(node)
        return node_key in self._errors_registry

    def get_connection_error_result(self, node: Dict) -> Optional[Dict]:
        """Получение отформатированного результата ошибки для узла"""
        node_key = self._get_node_key(node)
        if node_key not in self._errors_registry:
            return None

        error_data = self._errors_registry[node_key]

        # Создаем отформатированный результат при первом запросе
        if error_data['formatted_result'] is None:
            error_data['formatted_result'] = self._format_connection_error_result(
                error_data['node'],
                error_data['error_message']
            )

        return error_data['formatted_result']

    def get_all_connection_errors(self) -> List[Dict]:
        """Получение всех зарегистрированных ошибок соединения"""
        errors = []
        for error_data in self._errors_registry.values():
            if error_data['formatted_result'] is None:
                error_data['formatted_result'] = self._format_connection_error_result(
                    error_data['node'],
                    error_data['error_message']
                )
            errors.append(error_data['formatted_result'])

        logger.info(f"📋 Получено {len(errors)} ошибок SSH соединений из реестра")
        return errors

    def get_error_count(self) -> int:
        """Получение количества зарегистрированных ошибок"""
        return len(self._errors_registry)

    def _format_connection_error_result(self, node: Dict, error_msg: str) -> Dict:
        """
        Форматирование результата с ошибкой подключения
        """
        node_name = node.get('name', node['ip'])
        node_ip = node['ip']
        node_port = node.get('port', 22)

        # Создаем фиктивное правило для форматирования
        class ConnectionRule:
            id = "ssh_connection"
            name = "SSH соединение"
            solution = "Устраните проблемы с сетевым подключением или настройками SSH"

        rule = ConnectionRule()

        formatted_details = f"""Ошибка подключения к узлу {node_name} ({node_ip}:{node_port})

Сообщение об ошибке: {error_msg}

Диагностика:
• Проверьте доступность порта {node_port}: telnet {node_ip} {node_port} или nc -zv {node_ip} {node_port}
• Убедитесь, что SSH сервис запущен на узле
• Проверьте правильность учетных данных (имя пользователя, пароль/SSH ключ)
• Проверьте настройки firewall и сетевые политики
• Проверьте корректность DNS разрешения имени узла

Рекомендуемые действия:
1. Проверить статус SSH сервиса на узле
2. Проверить настройки аутентификации
3. Проверить журналы SSH на целевом узле
4. Проверить сетевую доступность порта {node_port}"""

        result = self._result_formatter.error_result(
            rule,
            error_msg,
            f"Не удалось установить SSH соединение с узлом {node_name}"
        )

        # Дополняем результат специфичной информацией
        result.update({
            'name': f'SSH соединение - {node_name}',
            'details': formatted_details,
            'node': {
                'ip': node_ip,
                'name': node_name,
                'port': node_port
            },
            'connection_error': True,
            'inspector_type': 'node_connection',
            'error_source': 'ssh_connection_manager'
        })

        return result

    @staticmethod
    def _get_node_key(node: Dict) -> str:
        """Генерация уникального ключа для узла"""
        return f"{node['ip']}:{node.get('port', 22)}"


class NodeInspector(BaseInspector):
    """
    Инспектор узлов с гарантией единого отображения ошибок SSH
    """

    def __init__(self, config: List[Dict[str, Any]], enable_concurrent: bool = True,
                 max_workers: int = 5, timeout: int = 30, enable_security_check: bool = True):
        """
        Инициализация инспектора узлов
        """
        inspector_config = {"nodes": config}
        super().__init__(inspector_config)

        self.nodes = config
        self.enable_concurrent = enable_concurrent
        self.max_workers = min(max_workers, len(config)) if enable_concurrent else 1
        self.timeout = timeout
        self.enable_security_check = enable_security_check

        # Менеджер ошибок SSH
        self.ssh_error_manager = SSHConnectionErrorManager()

        # Проверка безопасности
        self.security_checker = CommandSecurityChecker()
        logger.info("🔒 Проверка безопасности принудительно включена")

        # Локальный кэш статусов соединений для текущей проверки
        self.connection_status_cache = {}

        # Статистика выполнения
        self.execution_stats = {
            'total_nodes': len(config),
            'available_nodes': 0,
            'unavailable_nodes': 0,
            'total_node_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'blocked_by_security': 0,
            'security_warnings': 0,
            'total_time': 0
        }

        logger.info(f"Инспектор узлов инициализирован - узлов: {len(config)}")

    @property
    def inspector_type(self) -> str:
        return "node"

    def run_inspection(self, cluster_name: str, rule_ids: List[str] = None) -> InspectionResult:
        """
        Выполнение проверки с гарантией единого отображения ошибок SSH
        """
        logger.info(f"🔍 Начало проверки узлов - кластер: {cluster_name}")

        # Сбрасываем реестр ошибок перед началом новой проверки
        self.ssh_error_manager.reset_for_inspection()

        # Сбрасываем локальный кэш статусов
        self.connection_status_cache = {}

        # Выполняем проверку SSH соединения и определяем доступные узлы
        available_nodes = self._check_all_node_connections()
        self.execution_stats['available_nodes'] = len(available_nodes)
        self.execution_stats['unavailable_nodes'] = len(self.nodes) - len(available_nodes)

        # Если нет доступных узлов, возвращаем только ошибки SSH
        if not available_nodes:
            logger.error("❌ Нет доступных узлов для проверки")
            ssh_errors = self.ssh_error_manager.get_all_connection_errors()
            return InspectionResult(
                inspector_type=self.inspector_type,
                cluster_name=cluster_name,
                items=ssh_errors,
                stats=self.execution_stats
            )

        # Выполняем правила проверки только на доступных узлах
        result = super().run_inspection(cluster_name, rule_ids)

        # Добавляем ошибки SSH соединений в начало отчета
        ssh_errors = self.ssh_error_manager.get_all_connection_errors()
        if ssh_errors:
            result.items = ssh_errors + result.items
            logger.info(f"📋 Добавлено {len(ssh_errors)} ошибок SSH соединений в отчет")

        # Обновляем статистику
        result.stats = self.execution_stats

        logger.info(f"✅ Проверка завершена - всего результатов: {len(result.items)}")
        logger.info(f"📊 Статистика: {self.execution_stats['available_nodes']} доступных, {self.execution_stats['unavailable_nodes']} недоступных узлов")

        return result

    def _check_all_node_connections(self) -> List[Dict]:
        """
        Проверка SSH соединения со всеми узлами
        Возвращает список доступных узлов
        """
        logger.info("🔌 Проверка SSH соединения со всеми узлами...")

        available_nodes = []

        for node in self.nodes:
            node_key = self.ssh_error_manager._get_node_key(node)
            node_name = node.get('name', node['ip'])

            # Проверяем, не было ли уже ошибки для этого узла
            if self.ssh_error_manager.has_connection_error(node):
                logger.debug(f"Узел {node_name} уже имеет ошибку SSH, пропускаем")
                continue

            # Проверяем кэш статусов
            if node_key in self.connection_status_cache:
                status = self.connection_status_cache[node_key]
                node['connection_status'] = status
                if status['success']:
                    available_nodes.append(node)
                else:
                    # Регистрируем ошибку в менеджере
                    self.ssh_error_manager.register_connection_error(node, status['message'])
                continue

            # Выполняем проверку соединения
            logger.info(f"Проверка SSH соединения с узлом: {node_name}")
            success, message = test_node_connection(node)

            # Сохраняем статус
            status = {'success': success, 'message': message}
            self.connection_status_cache[node_key] = status
            node['connection_status'] = status

            if success:
                available_nodes.append(node)
                logger.info(f"✅ SSH соединение с узлом {node_name} успешно")
            else:
                logger.error(f"❌ SSH соединение с узлом {node_name} недоступно: {message}")
                # Регистрируем ошибку в менеджере
                self.ssh_error_manager.register_connection_error(node, message)

        logger.info(f"Проверка соединения завершена. Доступно: {len(available_nodes)}, Недоступно: {len(self.nodes) - len(available_nodes)}")
        return available_nodes

    def _apply_rule(self, rule: Rule, context: Dict) -> Union[Dict, List[Dict], None]:
        """
        Применение правила проверки только к доступным узлам
        """
        logger.info(f"🎯 Применение правила: {rule.id} - {rule.name}")
        rule_start_time = time.time()

        # Получаем конфигурацию правила
        command = self.get_rule_config(rule, 'execution.command', '')
        assertions = self.get_rule_config(rule, 'assertions', [])

        # Проверка безопасности команды
        if self.enable_security_check and command:
            is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
            if not is_safe:
                logger.error(f"Правило {rule.id} заблокировано по безопасности: {risk_desc}")
                self.execution_stats['blocked_by_security'] += 1
                return self._format_security_blocked_result(rule, risk_desc, command)

        # Фильтрация узлов по селектору
        node_selector = self.get_rule_config(rule, 'scope.node_selector', {})
        target_nodes = self._filter_nodes_by_selector(self.nodes, node_selector)

        if not target_nodes:
            logger.warning(f"Правило {rule.id} - нет подходящих узлов")
            return None

        # Фильтруем только узлы с успешным SSH соединением
        available_nodes = []
        for node in target_nodes:
            node_name = node.get('name', node['ip'])

            # Пропускаем узлы с ошибками SSH соединения
            if self.ssh_error_manager.has_connection_error(node):
                logger.debug(f"Правило {rule.id} - узел {node_name} имеет ошибку SSH, пропускаем")
                continue

            # Проверяем статус соединения
            status = node.get('connection_status', {})
            if status.get('success', False):
                available_nodes.append(node)
            else:
                logger.warning(f"Правило {rule.id} - узел {node_name} не прошел проверку соединения")

        logger.info(f"Правило {rule.id} - доступно узлов: {len(available_nodes)} из {len(target_nodes)}")

        # Если нет доступных узлов, правило не выполняется
        if not available_nodes:
            logger.warning(f"Правило {rule.id} - нет доступных узлов для выполнения")
            return None

        # Выполнение правила на доступных узлах
        if self.enable_concurrent and len(available_nodes) > 1:
            node_results = self._execute_rule_concurrently(rule, command, assertions, available_nodes)
        else:
            node_results = self._execute_rule_sequentially(rule, command, assertions, available_nodes)

        # Обновление статистики
        rule_duration = time.time() - rule_start_time
        self.execution_stats['total_node_executions'] += len(available_nodes)
        self.execution_stats['total_time'] += rule_duration

        logger.info(f"✅ Правило {rule.id} выполнено за {rule_duration:.2f}сек")
        return node_results

    def _execute_rule_concurrently(self, rule: Rule, command: str,
                                 assertions: List[Dict], target_nodes: List[Dict]) -> List[Dict]:
        """Параллельное выполнение правила только на доступных узлах"""
        node_results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_node = {}
            for node in target_nodes:
                # Дополнительная проверка перед выполнением
                if self.ssh_error_manager.has_connection_error(node):
                    continue

                future = executor.submit(
                    self._execute_rule_on_single_node,
                    rule, command, assertions, node
                )
                future_to_node[future] = node

            for future in as_completed(future_to_node, timeout=self.timeout * len(target_nodes)):
                node = future_to_node[future]
                try:
                    result = future.result(timeout=self.timeout)
                    if result:
                        node_results.append(result)
                        self.execution_stats['successful_executions'] += 1
                except Exception as e:
                    logger.error(f"Ошибка выполнения на узле {node.get('name', node['ip'])}: {str(e)}")
                    # Не создаем ошибку выполнения для узлов с ошибкой SSH
                    if not self.ssh_error_manager.has_connection_error(node):
                        error_result = self._format_execution_error_result(rule, node, str(e))
                        if error_result:
                            node_results.append(error_result)
                    self.execution_stats['failed_executions'] += 1

        return node_results

    def _execute_rule_sequentially(self, rule: Rule, command: str,
                                 assertions: List[Dict], target_nodes: List[Dict]) -> List[Dict]:
        """Последовательное выполнение правила только на доступных узлах"""
        node_results = []

        for node in target_nodes:
            # Дополнительная проверка перед выполнением
            if self.ssh_error_manager.has_connection_error(node):
                continue

            try:
                result = self._execute_rule_on_single_node(rule, command, assertions, node)
                if result:
                    node_results.append(result)
                    self.execution_stats['successful_executions'] += 1
            except Exception as e:
                logger.error(f"Ошибка выполнения на узле {node.get('name', node['ip'])}: {str(e)}")
                # Не создаем ошибку выполнения для узлов с ошибкой SSH
                if not self.ssh_error_manager.has_connection_error(node):
                    error_result = self._format_execution_error_result(rule, node, str(e))
                    if error_result:
                        node_results.append(error_result)
                self.execution_stats['failed_executions'] += 1

        return node_results

    def _execute_rule_on_single_node(self, rule: Rule, command: str,
                                   assertions: List[Dict], node: Dict) -> Optional[Dict]:
        """Выполнение правила на одном узле (только если узел доступен)"""
        node_name = node.get('name', node['ip'])

        # Финальная проверка: убеждаемся, что нет ошибки SSH соединения
        if self.ssh_error_manager.has_connection_error(node):
            logger.warning(f"Узел {node_name} имеет ошибку SSH, пропускаем выполнение")
            return None

        # Выполнение команды
        output, error = self._execute_command(command, node)

        if error:
            # Если произошла ошибка SSH, регистрируем ее и больше не выполняем правила на этом узле
            if self._is_ssh_connection_error(error):
                self.ssh_error_manager.register_connection_error(node, error)
                return None
            return self._format_execution_error_result(rule, node, error)
        else:
            # Оценка утверждений
            variables = {
                'output': output.strip(),
                'node_ip': node['ip'],
                'node_name': node_name
            }
            return self._evaluate_assertions(rule, assertions, variables, node)

    def _is_ssh_connection_error(self, error_msg: str) -> bool:
        """Проверяет, является ли ошибка связанной с SSH соединением"""
        ssh_keywords = [
            'connection', 'connect', 'ssh', 'timeout', 'refused',
            'authentication', 'auth', 'handshake', 'socket',
            'network', 'unreachable', 'closed', 'reset'
        ]
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in ssh_keywords)

    def _execute_command(self, command: str, node: Dict) -> Tuple[str, str]:
        """Выполнение команды на узле (только если узел доступен)"""
        try:
            node_name = node.get('name', node['ip'])

            # Финальная проверка перед выполнением
            if self.ssh_error_manager.has_connection_error(node):
                return "", "SSH соединение недоступно"

            # Проверка безопасности команды
            if self.enable_security_check:
                is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                if not is_safe:
                    error_msg = f"Команда заблокирована по безопасности: {risk_desc}"
                    logger.error(f"Узел {node_name}: {error_msg}")
                    return "", error_msg

            # Выполнение команды через SSH
            with NodeConnection(node) as conn:
                if not conn.connected:
                    error_msg = "SSH подключение не удалось"
                    logger.error(f"Узел {node_name}: {error_msg}")
                    # Регистрируем ошибку SSH
                    self.ssh_error_manager.register_connection_error(node, error_msg)
                    return "", error_msg

                success, stdout, stderr = conn.execute_command(command)
                if success:
                    return stdout, ""
                else:
                    # Проверяем, является ли ошибка связанной с SSH
                    if self._is_ssh_connection_error(stderr):
                        self.ssh_error_manager.register_connection_error(node, stderr)
                    return stdout, stderr

        except Exception as e:
            error_msg = f"Ошибка выполнения команды: {str(e)}"
            logger.error(f"Узел {node.get('name', node['ip'])}: {error_msg}")

            # Проверяем, является ли исключение связанным с SSH
            if self._is_ssh_connection_error(error_msg):
                self.ssh_error_manager.register_connection_error(node, error_msg)

            return "", error_msg

    def _evaluate_assertions(self, rule: Rule, assertions: List[Dict],
                            variables: Dict[str, Any], node: Dict) -> Dict:
        """Оценка утверждений правила"""
        assertion_result = self.rule_processor.evaluate_assertions(assertions, variables)

        if assertion_result['passed']:
            status = "passed"
            severity = "info"
            description = f"{rule.name}: проверка пройдена"
            details = "Состояние системы соответствует требованиям"
            solution = ""
        else:
            status = "failed"
            severity = assertion_result['severity']
            description = assertion_result['description'].replace("Утверждение не выполнено: ", "")
            details = "Детали неудачной проверки:\n" + "\n".join(
                [f"- {fa['name']}: {fa['description']}" for fa in assertion_result['failed_assertions']]
            )
            solution = rule.solution

        # Форматирование результата
        result = self.rule_processor.format_rule_result(
            rule=rule,
            status=status,
            description=description,
            severity=severity,
            details=details,
            solution=solution
        )

        # Добавление информации об узле
        node_name = node.get('name', node['ip'])
        result['name'] = f"{rule.name} - {node_name}"
        result['node'] = {'ip': node['ip'], 'name': node_name}
        result['variables'] = variables

        return result

    def _filter_nodes_by_selector(self, nodes: List[Dict], node_selector: Dict) -> List[Dict]:
        """Фильтрация узлов по селектору"""
        if not node_selector:
            return nodes

        filtered_nodes = []
        for node in nodes:
            node_labels = node.get('labels', {})
            match = True
            for label_key, label_value in node_selector.items():
                if label_key not in node_labels or str(node_labels[label_key]) != str(label_value):
                    match = False
                    break
            if match:
                filtered_nodes.append(node)

        return filtered_nodes

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """Валидация конфигурации правила"""
        issues = []
        command = self.get_rule_config(rule, 'execution.command', '')
        if not command:
            issues.append("Отсутствует команда выполнения")
        else:
            if self.enable_security_check:
                is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                if not is_safe:
                    issues.append(f"Проверка безопасности не пройдена: {risk_desc}")

        assertions = self.get_rule_config(rule, 'assertions', [])
        if not assertions:
            issues.append("Отсутствуют утверждения")

        return issues

    def _should_apply_rule(self, rule: Rule, context: Dict) -> bool:
        """Определение применимости правила"""
        node_selector = self.get_rule_config(rule, 'scope.node_selector', {})
        return not node_selector or any(
            self._filter_nodes_by_selector(self.nodes, node_selector)
        )

    def _format_security_blocked_result(self, rule: Rule, risk_desc: str, command: str) -> Dict:
        """Форматирование результата блокировки по безопасности"""
        return self.rule_processor.result_formatter.error_result(
            rule,
            f"Команда содержит риски безопасности: {risk_desc}",
            "Проверка безопасности не пройдена"
        )

    def _format_execution_error_result(self, rule: Rule, node: Dict, error_msg: str) -> Optional[Dict]:
        """Форматирование результата ошибки выполнения"""
        # Не создаем ошибку выполнения для узлов с ошибкой SSH соединения
        if self.ssh_error_manager.has_connection_error(node):
            return None

        node_name = node.get('name', node['ip'])
        result = self.rule_processor.result_formatter.error_result(
            rule,
            error_msg,
            f"Ошибка выполнения на узле {node_name}"
        )
        result['node'] = {'ip': node['ip'], 'name': node_name}
        result['name'] = f"{rule.name} - {node_name}"
        return result

    def get_execution_stats(self) -> Dict:
        """Получение статистики выполнения"""
        stats = self.execution_stats.copy()
        stats.update({
            'concurrent_mode': self.enable_concurrent,
            'max_workers': self.max_workers,
            'timeout': self.timeout,
            'security_enabled': self.enable_security_check,
            'ssh_connection_errors': self.ssh_error_manager.get_error_count()
        })

        if stats['total_node_executions'] > 0:
            stats['success_rate'] = (stats['successful_executions'] / stats['total_node_executions'] * 100)
        else:
            stats['success_rate'] = 0

        return stats

    def print_execution_summary(self):
        """Вывод сводки выполнения"""
        stats = self.get_execution_stats()
        print(f"\n=== Сводка выполнения проверки узлов ===")
        print(f"Всего узлов: {stats['total_nodes']}")
        print(f"Доступных узлов: {stats['available_nodes']}")
        print(f"Недоступных узлов: {stats['unavailable_nodes']}")
        print(f"Ошибок SSH соединений: {stats['ssh_connection_errors']}")
        print(f"Выполнений на узлах: {stats['total_node_executions']}")
        print(f"Успешных выполнений: {stats['successful_executions']}")
        print(f"Неудачных выполнений: {stats['failed_executions']}")
        print(f"Успешность: {stats['success_rate']:.1f}%")
        print(f"Общее время: {stats['total_time']:.2f}сек")
        print(f"========================\n")

    @classmethod
    def create_optimized(cls, config: List[Dict[str, Any]]) -> 'NodeInspector':
        """Создание оптимизированного инспектора"""
        node_count = len(config)
        if node_count <= 3:
            max_workers = node_count
            timeout = 30
        elif node_count <= 10:
            max_workers = min(5, node_count)
            timeout = 25
        else:
            max_workers = min(10, node_count)
            timeout = 20

        return cls(
            config=config,
            enable_concurrent=node_count > 1,
            max_workers=max_workers,
            timeout=timeout
        )