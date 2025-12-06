#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Командный безопасный чекер - предотвращает выполнение опасных команд
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Уровень риска"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CommandSecurityChecker:
    """
    Командный безопасный чекер - принудительный режим белого списка, разрешает только операции чтения

    Важные принципы безопасности:
    - Инструмент инспекции может только наблюдать, не изменять
    - Все высокорисковые команды строго запрещены, без исключений
    - Не предоставляет никаких опций для снижения уровня безопасности
    """

    def __init__(self):
        """
        Инициализация командного безопасного чекера

        Примечание: Этот класс принудительно использует самый строгий режим безопасности, не принимает никаких параметров
        """
        # Принципы безопасности инструмента инспекции: только чтение, только наблюдение, не изменение
        self.strict_mode = True      # Принудительный строгий режим, нельзя изменить
        self.whitelist_only = True   # Принудительный режим белого списка, нельзя изменить
        self._init_security_rules()

    def _init_security_rules(self):
        """Инициализация правил безопасности - фокус на белом списке команд только для чтения"""

        # Абсолютно запрещенные команды (уровень CRITICAL) - любые операции изменения
        self.critical_commands = [
            # Удаление/перемещение/изменение файлов и директорий
            r'\brm\s+',                                     # Любая команда rm
            r'\bmv\s+',                                     # Любая команда mv
            r'\bcp\s+.*>\s*/',                             # Копирование с перезаписью системных файлов
            r'\bmkdir\s+',                                  # Создание директории
            r'\brmdir\s+',                                  # Удаление директории
            r'\btouch\s+',                                  # Создание/изменение временной метки файла

            # Изменение прав и владельца
            r'\bchmod\s+',                                  # Любое изменение прав
            r'\bchown\s+',                                  # Изменение владельца
            r'\bchgrp\s+',                                  # Изменение группы

            # Управление системными сервисами (запрещены только операции изменения, разрешены is-active/status/show и т.д. только чтение)
            r'\bsystemctl\s+(start|stop|restart|reload|enable|disable|mask|unmask|kill|reset-failed)\b', # Управление сервисами
            r'\bservice\s+\w+\s+(start|stop|restart|reload)\b',           # Команда service
            r'\binit\s+[0-6]',                             # Изменение уровня запуска системы
            r'\bshutdown\s+',                              # Выключение системы
            r'\breboot\s*',                                # Перезагрузка системы
            r'\bhalt\s*',                                  # Остановка системы

            # Управление процессами
            r'\bkill\s+(-[0-9]+|\w+)',                     # Убийство процесса
            r'\bkillall\s+',                               # Массовое убийство процессов
            r'\bpkill\s+',                                 # Убийство процессов по шаблону

            # Опасные системные команды
            r'\bdd\s+.*of=',                               # Операция записи dd
            r'\bmkfs\.',                                   # Форматирование файловой системы
            r'\bmount\s+',                                 # Операция монтирования
            r'\bumount\s+',                                # Операция размонтирования
            r'\bfsck\s+',                                  # Проверка и ремонт файловой системы

            # Управление пакетами
            r'\bapt\s+(install|remove|purge|upgrade)',     # Управление пакетами Debian
            r'\bapt-get\s+(install|remove|purge|upgrade)', # Операции apt-get
            r'\byum\s+(install|remove|erase|update)',      # Управление пакетами RedHat
            r'\bdnf\s+(install|remove|erase|update)',      # Управление пакетами Fedora
            r'\bpip\s+install',                            # Установка пакетов Python
            r'\bnpm\s+install',                            # Установка пакетов Node.js

            # Изменение сетевой конфигурации
            r'\bifconfig\s+\w+\s+(up|down)',               # Включение/выключение сетевого интерфейса
            r'\bip\s+(addr|link|route)\s+(add|del|set)',   # Изменение IP-конфигурации
            r'\biptables\s+(-A|-D|-I|-R|-F|-X)',          # Изменение правил firewall
            r'\bnetplan\s+apply',                          # Применение сетевой конфигурации

            # Управление запланированными задачами
            r'\bcrontab\s+(-e|-r)',                        # Редактирование/удаление cron
            r'\bat\s+',                                    # Запланированная задача

            # Перенаправление файлов и пайпы (могут изменять файлы)
            r'>\s*[^/]*/',                                 # Перенаправление в файл
            r'>>\s*[^/]*/',                                # Добавление перенаправления в файл

            # Удаленное выполнение и загрузка
            r'(wget|curl).*\|\s*(sh|bash|python|perl)',   # Загрузка и выполнение
            r'(wget|curl).*\|.*sh',                        # Загрузка и выполнение (упрощенная версия)
            r'\bscp\s+.*:',                                # Удаленное копирование
            r'\brsync\s+.*:',                              # Удаленная синхронизация

            # Компиляция и сборка
            r'\bmake\s+(install|clean)',                   # Компиляция и установка
            r'\b\./configure\s+',                          # Скрипт конфигурации

            # Изменение параметров ядра и системы
            r'\bsysctl\s+-w',                              # Изменение параметров ядра
            r'\becho\s+.*>\s*/proc/',                      # Изменение параметров proc
            r'\bmodprobe\s+',                              # Загрузка модуля ядра
            r'\brmmod\s+',                                 # Выгрузка модуля ядра
        ]

        # Безопасные команды только для чтения белый список (явно разрешенные команды)
        self.safe_readonly_patterns = [
            # Просмотр системной информации
            r'^\s*cat\s+(/proc/|/sys/|/etc/hostname|/etc/os-release)',  # Просмотр системных файлов
            r'^\s*less\s+(/var/log/|/proc/|/sys/)',        # Просмотр логов и системной информации
            r'^\s*more\s+(/var/log/|/proc/|/sys/)',        # Просмотр содержимого файлов
            r'^\s*head\s+(-\d+\s+)?(/var/log/|/proc/|/sys/|/etc/)', # Просмотр начала файла
            r'^\s*tail\s+(-\d+\s+)?(/var/log/|/proc/|/sys/)',        # Просмотр конца файла
            r'^\s*(grep|awk|sed)\s+.*(/var/log/|/proc/|/sys/)',      # Обработка текста только чтение

            # Просмотр состояния системы
            r'^\s*(uname|hostname|whoami|id|date|uptime)\s*',         # Основная системная информация
            r'^\s*(w|who|last|lastlog)\s*',                           # Информация о пользователях
            r'^\s*(ps|top|htop|pstree|pgrep)\s+',                     # Информация о процессах
            r'^\s*(free|vmstat|iostat|sar)\s+',                       # Системные ресурсы
            r'^\s*(df|du|lsblk|lsof|fuser)\s+',                       # Информация о дисках и файлах

            # Просмотр сетевого состояния
            r'^\s*(netstat|ss)\s+',                                   # Состояние сетевых соединений
            r'^\s*lsof\s+-i',                                         # Открытые сетевые файлы
            r'^\s*iptables\s+-L',                                     # Просмотр правил firewall
            r'^\s*ip\s+(addr|link|route)\s*(show|list)?',             # Просмотр IP-конфигурации
            r'^\s*ifconfig\s*$',                                      # Просмотр сетевых интерфейсов (без параметров)

            # Просмотр файловой системы
            r'^\s*ls\s+',                                             # Список файлов
            r'^\s*find\s+.*-type\s+f.*-name',                        # Поиск файлов
            r'^\s*locate\s+',                                         # Локация файлов
            r'^\s*which\s+',                                          # Поиск пути команды
            r'^\s*whereis\s+',                                        # Поиск связанных с командой файлов

            # Команды Kubernetes только для чтения
            r'^\s*kubectl\s+(get|describe|logs|explain|api-resources|api-versions|version|cluster-info)\s+', # Команды просмотра K8s
            r'^\s*docker\s+(ps|images|version|info|logs)\s+',         # Команды просмотра Docker

            # Просмотр логов
            r'^\s*journalctl\s+(-u\s+\w+\s+)?(-f\s+)?(-n\s+\d+\s+)?(-S\s+.*)?$', # Просмотр логов systemd
            r'^\s*dmesg\s*$',                                         # Сообщения ядра

            # Другие команды только для чтения
            r'^\s*history\s*$',                                       # История команд
            r'^\s*env\s*$',                                           # Переменные окружения
            r'^\s*printenv\s*',                                       # Печать переменных окружения
            r'^\s*echo\s+\$\w+',                                      # Печать значения переменной
            r'^\s*printf\s+',                                         # Форматированный вывод
        ]
        self.safe_readonly_patterns.extend([
            r'^\s*(awk|wc|tail|head|xargs|grep|sed)\b.*',
            r'^\s*systemctl\s+(is-active|status|show)\b.*',
            r'^\s*service\s+\w+\s+(status)\b.*',
            r'^\s*echo\b.*',  # Разрешить echo любое содержимое
        ])

    def check_command_security(self, command: str) -> Tuple[bool, RiskLevel, str]:
        """
        Проверка безопасности команды - режим приоритета белого списка

        Args:
            command: Команда для проверки

        Returns:
            (безопасна ли, уровень риска, описание риска)
        """
        command = command.strip()

        logger.info(f"🔍 Начинается проверка безопасности - Команда: {command[:100]}{'...' if len(command) > 100 else ''}")

        if not command:
            logger.info("Пустая команда, считается безопасной")
            return True, RiskLevel.LOW, "Пустая команда"

        # Шаг первый: Проверка, является ли команда явно безопасной только для чтения (белый список)
        if self._is_safe_readonly_command(command):
            logger.info("✅ Команда прошла проверку белого списка")
            return True, RiskLevel.LOW, "Безопасная команда только для чтения"

        # Шаг второй: Проверка, содержит ли команда абсолютно запрещенные операции (черный список)
        if self._contains_critical_operations(command):
            risk_level, risk_desc = self._analyze_command_risk(command)
            logger.error(f"❌ Обнаружена запрещенная операция изменения: {command[:100]}... Риск: {risk_desc}")
            return False, risk_level, risk_desc

        # Шаг третий: Если включен режим только белого списка, отклонить все не явно разрешенные команды
        if self.whitelist_only:
            logger.warning(f"⚠️ Режим только белого списка: Команда не в безопасном белом списке: {command[:100]}...")
            return False, RiskLevel.HIGH, "Команда не в безопасном белом списке, инструмент инспекции разрешает только команды просмотра только для чтения"

        # Шаг четвертый: Традиционный анализ риска (для режима совместимости)
        risk_level, risk_desc = self._analyze_command_risk(command)

        if risk_level == RiskLevel.CRITICAL:
            logger.error(f"Обнаружена команда критического риска: {command[:100]}... Риск: {risk_desc}")
            return False, risk_level, risk_desc

        if self.strict_mode and risk_level == RiskLevel.HIGH:
            logger.warning(f"В строгом режиме отклонена команда высокого риска: {command[:100]}... Риск: {risk_desc}")
            return False, risk_level, risk_desc

        if risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
            logger.warning(f"Обнаружена рискованная команда: {command[:100]}... Уровень риска: {risk_level.value}, Описание: {risk_desc}")
            return not self.strict_mode, risk_level, risk_desc

        return True, RiskLevel.LOW, "Команда прошла проверку безопасности"

    def _contains_critical_operations(self, command: str) -> bool:
        """Проверка, содержит ли команда абсолютно запрещенные операции изменения (разделение каждого подкоманды для суждения, избежание ошибочного суждения комбинаций только чтения)"""
        cmd = command.strip()
        sep_pattern = r'(\|\||&&)'
        def strip_redirect(s):
            s = re.split(r'>+.*', s)[0].strip()
            return s
        sub_cmds = re.split(sep_pattern, cmd)
        for sub in sub_cmds:
            sub = sub.strip()
            if not sub or sub in {'|', '||', '&&'}:
                continue
            if sub.startswith('sudo '):
                sub = sub[5:].lstrip()
            sub = strip_redirect(sub)
            for pattern in self.critical_commands:
                if re.search(pattern, sub, re.IGNORECASE):
                    return True
        return False

    def _is_safe_readonly_command(self, command: str) -> bool:
        """Проверка, является ли команда безопасной только для чтения, поддерживает префикс sudo, комбинации пайп/логических, удаление перенаправления"""
        cmd = command.strip()
        sep_pattern = r'(\|\||&&)'

        logger.info(f"🔍 Проверка белого списка - Исходная команда: {cmd}")

        def strip_redirect(s):
            s = re.split(r'>+.*', s)[0].strip()
            return s

        sub_cmds = re.split(sep_pattern, cmd)
        logger.info(f"Разделенные подкоманды: {sub_cmds}")

        for i, sub in enumerate(sub_cmds):
            sub = sub.strip()
            if not sub or sub in {'|', '||', '&&'}:
                logger.debug(f"Подкоманда {i}: '{sub}' (разделитель, пропустить)")
                continue

            if sub.startswith('sudo '):
                sub = sub[5:].lstrip()
                logger.info(f"Подкоманда {i}: После удаления префикса sudo: '{sub}'")

            sub = strip_redirect(sub)
            logger.info(f"Подкоманда {i}: После удаления перенаправления: '{sub}'")

            matched = False
            for pattern in self.safe_readonly_patterns:
                if re.match(pattern, sub, re.IGNORECASE):
                    logger.info(f"✅ Подкоманда {i} соответствует шаблону белого списка: {pattern}")
                    matched = True
                    break

            if not matched:
                logger.warning(f"❌ Подкоманда {i} не соответствует ни одному шаблону белого списка: '{sub}'")
                return False

        logger.info("✅ Все подкоманды прошли проверку белого списка")
        return True

    def _analyze_command_risk(self, command: str) -> Tuple[RiskLevel, str]:
        """
        Анализ риска команды - идентификация рисковых шаблонов и уровней в команде

        Args:
            command: Команда для анализа

        Returns:
            (уровень риска, описание риска)
        """
        command = command.strip()

        if not command:
            return RiskLevel.LOW, "Пустая команда"

        risk_level = RiskLevel.LOW
        risk_desc = "Команда низкого риска"

        # Проверка риска каждой подкоманды
        sep_pattern = r'(\|\||&&)'
        sub_cmds = re.split(sep_pattern, command)
        for sub in sub_cmds:
            sub = sub.strip()
            if not sub or sub in {'|', '||', '&&'}:
                continue
            if sub.startswith('sudo '):
                sub = sub[5:].lstrip()
            sub_risk_level, sub_risk_desc = self._analyze_single_command_risk(sub)

            # Слияние уровней риска
            if sub_risk_level.value > risk_level.value:
                risk_level = sub_risk_level
                risk_desc = sub_risk_desc

        return risk_level, risk_desc

    def _analyze_single_command_risk(self, command: str) -> Tuple[RiskLevel, str]:
        """
        Анализ риска отдельной команды - идентификация рисковых шаблонов и уровней в отдельной команде

        Args:
            command: Команда для анализа

        Returns:
            (уровень риска, описание риска)
        """
        command = command.strip()

        if not command:
            return RiskLevel.LOW, "Пустая команда"

        # Проверка, является ли команда абсолютно запрещенной
        for pattern in self.critical_commands:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.CRITICAL, "Содержит абсолютно запрещенные операции изменения"

        # Проверка, является ли команда высокого риска
        high_risk_patterns = [
            r'\b(dd|mkfs|mount|umount|chmod|chown|chgrp|systemctl|service|kill|killall|pkill|reboot|shutdown|halt|apt-get|yum|dnf|pip|npm)\b',
            r'\b(find|locate|grep|awk|sed|xargs|wc|sort|uniq|tee|cut|tr|head|tail)\s+.*[|&]', # Комбинации пайп/логических
        ]
        for pattern in high_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.HIGH, "Содержит команды или операции высокого риска"

        # Проверка, является ли команда среднего риска
        medium_risk_patterns = [
            r'\b(less|more|cat|echo|printf|env|printenv|history|journalctl|dmesg)\b', # Только для части параметров
            r'\b(systemctl|service)\s+\w+\s+(status|show|is-active)\b',           # Просмотр состояния только чтение
        ]
        for pattern in medium_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.MEDIUM, "Содержит команды или операции среднего риска"

        return RiskLevel.LOW, "Команда низкого риска"
