#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инспектор узлов с поддержкой параллельного выполнения и улучшенными функциями безопасности
"""

import logging
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple, Union

from inspectors.base_inspector import BaseInspector
from utils.inspection_result import InspectionResult
from utils.rule_loader import Rule
from utils.node_connection import NodeConnection
from utils.command_security import CommandSecurityChecker, RiskLevel

# Настройка логирования
logger = logging.getLogger(__name__)

class NodeInspector(BaseInspector):
    """
    Инспектор узлов - принудительный безопасный режим, разрешены только операции чтения

    Принципы безопасности:
    - Принудительное включение проверок безопасности, нельзя отключить
    - Разрешено выполнение только команд чтения
    - Все высокорисковые команды строго запрещены
    """

    def __init__(self, config: List[Dict[str, Any]], enable_concurrent: bool = True,
                 max_workers: int = 5, timeout: int = 30, enable_security_check: bool = True):
        """
        Инициализация инспектора узлов

        Args:
            config: список конфигураций узлов, содержащий информацию о подключении
            enable_concurrent: включить параллельное выполнение, по умолчанию True
            max_workers: максимальное количество рабочих потоков, по умолчанию 5
            timeout: время ожидания выполнения команды на одном узле (секунды), по умолчанию 30
            enable_security_check: включить проверки безопасности, по умолчанию True
        """
        self.nodes = config
        self.enable_concurrent = enable_concurrent
        self.max_workers = min(max_workers, len(config)) if enable_concurrent else 1
        self.timeout = timeout
        self.enable_security_check = enable_security_check  # Новый атрибут, по умолчанию True

        # Проверка безопасности принудительно включена, нельзя отключить
        self.security_checker = CommandSecurityChecker()
        logger.info("🔒 Проверка безопасности принудительно включена - разрешены только команды чтения")

        # Статистика
        self.stats = {
            'total_rules': 0,
            'total_node_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'blocked_by_security': 0,
            'security_warnings': 0,
            'total_time': 0
        }

        super().__init__({"nodes": config})

        logger.info(f"Инспектор узлов инициализирован - параллельный режим: {'включен' if enable_concurrent else 'отключен'}, "
                   f"максимум потоков: {self.max_workers}, таймаут: {timeout}сек, "
                   f"проверка безопасности: принудительно включена")

    @property
    def inspector_type(self) -> str:
        return "node"

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """
        Проверка валидности конфигурации правила (включая проверки безопасности)

        Args:
            rule: объект правила

        Returns:
            список проблем конфигурации, пустой список если проблем нет
        """
        issues = []

        # Проверка необходимой конфигурации команд
        command = self.get_rule_config(rule, 'execution.command', '')
        if not command:
            issues.append("Отсутствует необходимая команда выполнения (execution.command)")
        else:
            # Проверка безопасности
            if self.enable_security_check:
                is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                if not is_safe:
                    issues.append(f"Проверка безопасности не пройдена: {risk_desc}")
                elif risk_level != RiskLevel.LOW:  # Исправление: используем значения перечисления вместо строк
                    issues.append(f"Команда содержит риски ({risk_level.value}): {risk_desc}")

        # Проверка необходимой конфигурации утверждений
        assertions = self.get_rule_config(rule, 'assertions', [])
        if not assertions:
            issues.append("Отсутствует необходимая конфигурация утверждений (assertions)")

        return issues

    def _apply_rule(self, rule: Rule, context: Dict) -> List[Dict]:
        """
        Применение одного правила для проверки узла (с поддержкой параллелизма и проверок безопасности)

        Args:
            rule: применяемое правило
            context: контекст проверки

        Returns:
            список результатов проверки
        """
        logger.info(f"🎯 Начало выполнения правила для узла: {rule.id} - {rule.name}")
        rule_start_time = time.time()

        # Получение конфигурации команды и утверждений
        command = self.get_rule_config(rule, 'execution.command', '')
        assertions = self.get_rule_config(rule, 'assertions', [])

        logger.info(f"Правило {rule.id} конфигурация - команда: {command[:100]}{'...' if len(command) > 100 else ''}")
        logger.info(f"Правило {rule.id} конфигурация - количество утверждений: {len(assertions)}")

        # Проверка безопасности
        if self.enable_security_check and command:
            logger.info(f"Правило {rule.id} начало проверки безопасности...")
            is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)

            if not is_safe:
                logger.error(f"Правило {rule.id} команда заблокирована проверкой безопасности: {risk_desc}")
                self.stats['blocked_by_security'] += 1

                # Возврат результата с ошибкой безопасности
                error_result = self._format_error_result(rule,
                    f"Проверка безопасности не пройдена",
                    f"Команда содержит риски безопасности и заблокирована: {risk_desc}\nКоманда: {command[:100]}{'...' if len(command) > 100 else ''}")
                error_result['security_blocked'] = True
                error_result['risk_level'] = risk_level
                return [error_result]
            else:
                logger.info(f"Правило {rule.id} проверка безопасности пройдена - уровень риска: {risk_level}")

            if risk_level != 'low':
                logger.warning(f"Правило {rule.id} команда содержит риски безопасности: {risk_desc}")
                self.stats['security_warnings'] += 1
                # В строгом режиме, если режим не строгий, продолжаем выполнение но логируем предупреждение
        else:
            logger.info(f"Правило {rule.id} пропуск проверки безопасности (enable_security_check={self.enable_security_check}, command_length={len(command)})")

        # Получение селектора узлов и фильтрация узлов
        node_selector = self.get_rule_config(rule, 'scope.node_selector', {})
        logger.info(f"Правило {rule.id} селектор узлов: {node_selector}")
        logger.info(f"Правило {rule.id} всего доступных узлов: {len(self.nodes)}")

        target_nodes = self._filter_nodes_by_selector(self.nodes, node_selector)
        logger.info(f"Правило {rule.id} количество целевых узлов после фильтрации: {len(target_nodes)}")

        if not target_nodes:
            logger.warning(f"Правило {rule.id} нет подходящих узлов")
            # Добавление детальной информации об узлах в лог
            logger.info(f"Список доступных узлов: {[node.get('name', node.get('ip', 'unknown')) for node in self.nodes]}")
            if node_selector:
                logger.info(f"Требования селектора узлов: {node_selector}")
                for node in self.nodes:
                    node_labels = node.get('labels', {})
                    logger.info(f"Узел {node.get('name', node.get('ip'))} метки: {node_labels}")
            return []

        # Запись информации о целевых узлах
        target_node_names = [node.get('name', node.get('ip', 'unknown')) for node in target_nodes]
        logger.info(f"Правило {rule.id} целевые узлы: {target_node_names}")

        # Выбор режима выполнения: если включен параллелизм и узлов > 1, используем параллельный; иначе последовательный
        if self.enable_concurrent and len(target_nodes) > 1:
            logger.info(f"Правило {rule.id}: будет выполнено параллельно на {len(target_nodes)} узлах (максимум потоков: {self.max_workers})")
            node_results = self._execute_rule_concurrently(rule, command, assertions, target_nodes)
        else:
            logger.info(f"Правило {rule.id}: будет выполнено последовательно на {len(target_nodes)} узлах")
            node_results = self._execute_rule_sequentially(rule, command, assertions, target_nodes)

        rule_duration = time.time() - rule_start_time
        logger.info(f"✅ Правило {rule.id} выполнено, затрачено времени {rule_duration:.2f}сек, количество результатов: {len(node_results)}")

        # Обновление статистики
        self.stats['total_rules'] += 1
        self.stats['total_node_executions'] += len(target_nodes)
        self.stats['total_time'] += rule_duration

        return node_results

    def _execute_rule_concurrently(self, rule: Rule, command: str,
                                 assertions: List[Dict], target_nodes: List[Dict]) -> List[Dict]:
        """
        Параллельное выполнение правила на нескольких узлах

        Args:
            rule: объект правила
            command: выполняемая команда
            assertions: список утверждений
            target_nodes: список целевых узлов

        Returns:
            список результатов проверки всех узлов
        """
        node_results = []

        # Использование пула потоков для параллельного выполнения
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Отправка всех задач для узлов
            future_to_node = {}
            for node in target_nodes:
                future = executor.submit(
                    self._execute_rule_on_single_node,
                    rule, command, assertions, node
                )
                future_to_node[future] = node

            # Сбор результатов
            for future in as_completed(future_to_node, timeout=self.timeout * len(target_nodes)):
                node = future_to_node[future]
                node_name = node.get('name', node['ip'])

                try:
                    result = future.result(timeout=self.timeout)
                    node_results.append(result)
                    self.stats['successful_executions'] += 1
                    logger.debug(f"Узел {node_name} выполнение завершено")

                except Exception as e:
                    logger.error(f"Узел {node_name} выполнение не удалось: {str(e)}")
                    # Создание результата с ошибкой
                    error_result = self._format_error_result(rule,
                        f"Выполнение на узле не удалось", str(e))
                    error_result['name'] = f"{rule.name} - {node_name}"
                    error_result['node'] = {'ip': node['ip'], 'name': node.get('name', node['ip'])}
                    node_results.append(error_result)
                    self.stats['failed_executions'] += 1

        return node_results

    def _execute_rule_sequentially(self, rule: Rule, command: str,
                                 assertions: List[Dict], target_nodes: List[Dict]) -> List[Dict]:
        """
        Последовательное выполнение правила на нескольких узлах (оригинальный способ)

        Args:
            rule: объект правила
            command: выполняемая команда
            assertions: список утверждений
            target_nodes: список целевых узлов

        Returns:
            список результатов проверки всех узлов
        """
        node_results = []

        for node in target_nodes:
            try:
                result = self._execute_rule_on_single_node(rule, command, assertions, node)
                node_results.append(result)
                self.stats['successful_executions'] += 1

            except Exception as e:
                node_name = node.get('name', node['ip'])
                logger.error(f"Узел {node_name} выполнение не удалось: {str(e)}")

                error_result = self._format_error_result(rule,
                    f"Выполнение на узле не удалось", str(e))
                error_result['name'] = f"{rule.name} - {node_name}"
                error_result['node'] = {'ip': node['ip'], 'name': node.get('name', node['ip'])}
                node_results.append(error_result)
                self.stats['failed_executions'] += 1

        return node_results

    def _execute_rule_on_single_node(self, rule: Rule, command: str,
                                   assertions: List[Dict], node: Dict) -> Dict:
        """
        Выполнение правила на одном узле

        Args:
            rule: объект правила
            command: выполняемая команда
            assertions: список утверждений
            node: информация об узле

        Returns:
            результат проверки для этого узла
        """
        node_name = node.get('name', node['ip'])

        # Выполнение команды
        output, error = self._execute_command(command, node)

        if error:
            # Ошибка выполнения команды
            node_result = self._format_error_result(rule,
                f"Выполнение команды не удалось", error)
            node_result['name'] = f"{rule.name} - {node_name}"
            node_result['node'] = {'ip': node['ip'], 'name': node.get('name', node['ip'])}
        else:
            # Подготовка словаря переменных - упрощенная версия
            variables = {
                'output': output.strip(),  # Прямое использование вывода команды
                'node_ip': node['ip'],
                'node_name': node.get('name', node['ip'])
            }

            # Оценка утверждений
            node_result = self._evaluate_assertions(rule, assertions, variables, node)

        return node_result

        return node_results

    def _evaluate_assertions(self, rule: Rule, assertions: List[Dict],
                            variables: Dict[str, Any], node: Dict) -> Dict:
        """
        Оценка утверждений

        Args:
            rule: объект правила
            assertions: список утверждений
            variables: словарь переменных
            node: информация об узле

        Returns:
            результат оценки
        """
        # Оценка всех утверждений
        assertion_result = self.rule_processor.evaluate_assertions(assertions, variables)

        # Форматирование результата проверки на основе оценки утверждений
        if assertion_result['passed']:
            status = "passed"
            severity = "info"
            # Для пройденных проверок отображаем конкретный результат проверки в описании
            first_assertion = assertions[0] if assertions else {}
            first_assertion_desc = first_assertion.get('description', '')
            if first_assertion_desc:
                # Рендеринг шаблона для отображения конкретных значений
                rendered_desc = self.rule_processor.assertion_manager.render_template(first_assertion_desc, variables)
                description = f"{rule.name}: {rendered_desc}"
            else:
                description = f"{rule.name}: текущее значение {variables.get('output', 'N/A')}"
            details = "Проверка пройдена, состояние системы нормальное"
            solution = ""
        else:
            status = "failed"
            severity = assertion_result['severity']
            # Удаление префикса "Утверждение не выполнено:", прямое использование описания
            description = assertion_result['description'].replace("Утверждение не выполнено: ", "")

            # Построение детальной информации
            failed_assertions = assertion_result['failed_assertions']
            details = "Детали неудачной проверки:\n" + "\n".join(
                [f"- {fa['name']}: {fa['description']}" for fa in failed_assertions]
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

        # Изменение имени для включения информации об узле, для удобства отображения в UI
        node_name = node.get('name', node['ip'])
        result['name'] = f"{rule.name} - {node_name}"

        # Добавление информации об узле и информации о переменных
        result['node'] = {'ip': node['ip'], 'name': node.get('name', node['ip'])}
        result['variables'] = variables
        result['assertions'] = {
            'total': len(assertions),
            'failed': len(assertion_result.get('failed_assertions', [])),
            'failures': assertion_result.get('failed_assertions')
        }

        return result

    def _execute_command(self, command: str, node: Dict) -> Tuple[str, str]:
        """
        Выполнение команды на узле (включая аудит безопасности)

        Args:
            command: выполняемая команда
            node: информация об узле

        Returns:
            кортеж из вывода команды и информации об ошибке
        """
        try:
            # Получение базовой информации об узле
            ip = node.get('ip', 'unknown')
            port = node.get('port', 22)
            username = node.get('username', 'unknown')
            node_name = node.get('name', ip)

            # Финальная проверка безопасности перед выполнением (двойная защита)
            if self.enable_security_check:
                is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                if not is_safe:
                    error_msg = f"Проверка безопасности перед выполнением не пройдена: {risk_desc}"
                    logger.error(f"Узел {node_name} команда заблокирована: {error_msg}")
                    # Запись в лог аудита безопасности
                    self._log_security_audit(node_name, ip, username, command, "BLOCKED", risk_desc)
                    return "", error_msg
                elif risk_level != 'low':
                    # Запись в лог аудита рискованной команды
                    self._log_security_audit(node_name, ip, username, command, "RISKY", risk_desc)

            logger.info(f"Подключение к узлу {node_name} ({ip}:{port}) пользователь: {username}")

            # Проверка целостности конфигурации узла
            auth_type = node.get('auth_type', 'password')
            if auth_type == 'password' and not node.get('password'):
                error_msg = f"Ошибка конфигурации узла {node_name}: используется аутентификация по паролю, но пароль не предоставлен"
                logger.error(error_msg)
                return "", error_msg
            elif auth_type == 'key' and not node.get('key_path'):
                error_msg = f"Ошибка конфигурации узла {node_name}: используется аутентификация по ключу, но путь к ключу не предоставлен"
                logger.error(error_msg)
                return "", error_msg

            # Упрощенное отображение команды (если команда слишком длинная)
            display_command = command[:100] + "..." if len(command) > 100 else command
            logger.info(f"Выполнение команды на узле {node_name}: {display_command}")

            # Запись в лог аудита выполнения команды
            self._log_security_audit(node_name, ip, username, command, "EXECUTE", "Нормальное выполнение")

            # Использование SSH для выполнения команды
            with NodeConnection(node) as conn:
                if not conn.connected:
                    error_msg = f"Не удалось подключиться к узлу {node_name} ({ip}): SSH подключение не удалось"
                    logger.error(error_msg)
                    # Запись в лог аудита неудачного подключения
                    self._log_security_audit(node_name, ip, username, command, "CONN_FAILED", error_msg)
                    return "", error_msg

                success, stdout, stderr = conn.execute_command(command)
                if success:
                    logger.info(f"Команда на узле {node_name} выполнена успешно, длина вывода: {len(stdout)}")
                    # Запись в лог аудита успешного выполнения
                    self._log_security_audit(node_name, ip, username, command, "SUCCESS", f"Длина вывода: {len(stdout)}")
                    return stdout, ""
                else:
                    error_msg = f"Выполнение команды не удалось: {stderr}"
                    logger.error(f"Узел {node_name}: {error_msg}")
                    # Запись в лог аудита неудачного выполнения
                    self._log_security_audit(node_name, ip, username, command, "FAILED", error_msg)
                    return "", error_msg

        except ConnectionError as e:
            error_msg = f"Ошибка сетевого подключения: {str(e)}"
            logger.error(f"Не удалось подключиться к узлу {node.get('name', node.get('ip'))}: {error_msg}")
            return "", error_msg
        except TimeoutError as e:
            error_msg = f"Таймаут подключения: {str(e)}"
            logger.error(f"Таймаут подключения к узлу {node.get('name', node.get('ip'))}: {error_msg}")
            return "", error_msg
        except Exception as e:
            error_msg = f"Непредвиденная ошибка при выполнении команды: {str(e)}"
            logger.error(f"Узел {node.get('name', node.get('ip'))}: {error_msg}", exc_info=True)
            return "", error_msg

    def _filter_nodes_by_selector(self, nodes: List[Dict], node_selector: Dict) -> List[Dict]:
        """
        Фильтрация узлов по селектору

        Args:
            nodes: список узлов
            node_selector: конфигурация селектора узлов

        Returns:
            отфильтрованный список узлов
        """
        if not node_selector:
            return nodes

        filtered_nodes = []
        for node in nodes:
            # Проверка соответствия меток узла селектору
            node_labels = node.get('labels', {})
            match = True

            for label_key, label_value in node_selector.items():
                if label_key not in node_labels or str(node_labels[label_key]) != str(label_value):
                    match = False
                    break

            if match:
                filtered_nodes.append(node)

        return filtered_nodes

    def _should_apply_rule(self, rule: Rule, context: Dict) -> bool:
        """
        Определение, должно ли правило применяться в текущем контексте

        Args:
            rule: правило
            context: контекст

        Returns:
            следует ли применять правило
        """
        # Проверка селектора узлов
        node_selector = self.get_rule_config(rule, 'scope.node_selector', {})
        if not node_selector:
            # Нет селектора узлов, применяется ко всем узлам
            return True

        # Так как мы проходим по узлам в _apply_rule, здесь просто возвращаем True
        # Фактическая фильтрация узлов по меткам будет выполнена в _apply_rule
        return True

    def _format_error_result(self, rule: Rule, description: str, error_msg: str) -> Dict:
        """Форматирование результата с ошибкой"""
        return self.rule_processor.format_rule_result(
            rule=rule,
            status="error",
            description=description,
            severity="error",
            details=error_msg,
            solution="Пожалуйста, проверьте конфигурацию узла и сетевое подключение"
        )

    def _log_security_audit(self, node_name: str, node_ip: str, username: str,
                           command: str, action: str, details: str):
        """
        Запись в лог аудита безопасности

        Args:
            node_name: имя узла
            node_ip: IP узла
            username: имя пользователя
            command: выполняемая команда
            action: тип операции (EXECUTE, BLOCKED, RISKY, SUCCESS, FAILED, CONN_FAILED)
            details: детальная информация
        """
        import time
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # Сокращенное отображение команды
        short_command = command[:150] + '...' if len(command) > 150 else command

        # Выбор уровня логирования в зависимости от типа операции
        if action == "BLOCKED":
            log_level = logger.error
            status_icon = "🚫"
        elif action == "RISKY":
            log_level = logger.warning
            status_icon = "⚠️"
        elif action == "FAILED" or action == "CONN_FAILED":
            log_level = logger.error
            status_icon = "❌"
        else:
            log_level = logger.info
            status_icon = "✅"

        # Запись в лог аудита
        audit_msg = (f"[SECURITY_AUDIT] {status_icon} {timestamp} | "
                    f"Узел: {node_name}({node_ip}) | Пользователь: {username} | "
                    f"Действие: {action} | Команда: {short_command} | "
                    f"Детали: {details}")

        log_level(audit_msg)

        # Опционально: запись в специальный файл лога аудита безопасности
        try:
            audit_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'logs', 'security_audit.log')
            os.makedirs(os.path.dirname(audit_file), exist_ok=True)
            with open(audit_file, 'a', encoding='utf-8') as f:
                f.write(f"{audit_msg}\n")
        except Exception as e:
            logger.warning(f"Не удалось записать в файл лога аудита безопасности: {str(e)}")

    def get_security_stats(self) -> Dict:
        """Получение статистики безопасности"""
        return {
            'security_enabled': self.enable_security_check,
            'strict_mode': self.strict_security_mode,
            'blocked_by_security': self.stats.get('blocked_by_security', 0),
            'security_warnings': self.stats.get('security_warnings', 0),
            'total_commands_checked': self.stats.get('total_rules', 0)
        }

    def get_execution_stats(self) -> Dict:
        """Получение статистики выполнения (включая статистику безопасности)"""
        base_stats = {
            **self.stats,
            'average_time_per_rule': self.stats['total_time'] / max(self.stats['total_rules'], 1),
            'success_rate': self.stats['successful_executions'] / max(self.stats['total_node_executions'], 1) * 100,
            'concurrent_mode': self.enable_concurrent,
            'max_workers': self.max_workers,
            'timeout': self.timeout
        }

        # Добавление статистики безопасности
        base_stats.update(self.get_security_stats())
        return base_stats

    def print_execution_summary(self):
        """Печать сводки выполнения (включая информацию о безопасности)"""
        stats = self.get_execution_stats()

        print(f"\n=== Сводка выполнения проверки узлов ===")
        print(f"Режим выполнения: {'параллельный' if stats['concurrent_mode'] else 'последовательный'}")
        print(f"Проверка безопасности: {'включена' if stats['security_enabled'] else 'отключена'} "
              f"({'строгий режим' if stats.get('strict_mode') else 'мягкий режим'})")
        print(f"Всего правил: {stats['total_rules']}")
        print(f"Всего выполнений на узлах: {stats['total_node_executions']}")
        print(f"Успешных выполнений: {stats['successful_executions']}")
        print(f"Неудачных выполнений: {stats['failed_executions']}")
        if stats['security_enabled']:
            print(f"Блокировок по безопасности: {stats['blocked_by_security']}")
            print(f"Предупреждений безопасности: {stats['security_warnings']}")
        print(f"Успешность: {stats['success_rate']:.1f}%")
        print(f"Общее время: {stats['total_time']:.2f}сек")
        print(f"Среднее время на правило: {stats['average_time_per_rule']:.2f}сек")
        if stats['concurrent_mode']:
            print(f"Максимум потоков: {stats['max_workers']}")
        print(f"Настройка таймаута: {stats['timeout']}сек")
        print(f"========================\n")

    @classmethod
    def create_optimized(cls, config: List[Dict[str, Any]]) -> 'NodeInspector':
        """
        Создание оптимизированного инспектора узлов

        Args:
            config: список конфигураций узлов

        Returns:
            экземпляр инспектора узлов с оптимизированной конфигурацией
        """
        node_count = len(config)

        # Адаптивная конфигурация в зависимости от количества узлов
        if node_count <= 3:
            max_workers = node_count
            timeout = 30
        elif node_count <= 10:
            max_workers = min(5, node_count)
            timeout = 25
        elif node_count <= 20:
            max_workers = min(8, node_count)
            timeout = 20
        else:
            max_workers = min(10, node_count)
            timeout = 15

        return cls(
            config=config,
            enable_concurrent=node_count > 1,  # Не включать параллелизм для одного узла
            max_workers=max_workers,
            timeout=timeout
        )