// Constants for Help page content

export const SAFE_COMMANDS = [
  {
    category: 'Просмотр системных файлов',
    commands:
      'cat (для /proc/, /sys/, /etc/hostname, /etc/os-release), less, more, head, tail (для /var/log/, /proc/, /sys/, /etc/)',
  },
  {
    category: 'Поиск и фильтрация',
    commands:
      'grep, awk, sed (для /var/log/, /proc/, /sys/), find (только для поиска файлов), locate, which, whereis',
  },
  {
    category: 'Информация о системе',
    commands:
      'uname, hostname, whoami, id, date, uptime, w, who, last, lastlog, history, env, printenv, echo (переменные), printf, sestatus',
  },
  {
    category: 'Информация о процессах',
    commands: 'ps, top, htop, pstree, pgrep',
  },
  {
    category: 'Информация о ресурсах',
    commands: 'free, vmstat, iostat, sar, df, du, lsblk, lsof, fuser',
  },
  {
    category: 'Сетевая информация',
    commands:
      'netstat, ss, lsof -i, iptables -L (просмотр правил), ip (addr/link/route show), ifconfig (без параметров)',
  },
  {
    category: 'Логи',
    commands: 'journalctl (с параметрами просмотра), dmesg',
  },
  {
    category: 'Kubernetes команды',
    commands:
      'kubectl get, describe, logs, explain, api-resources, api-versions, version, cluster-info',
  },
  {
    category: 'Docker команды',
    commands: 'docker ps, images, version, info, logs',
  },
  {
    category: 'Системные сервисы (только чтение)',
    commands: 'systemctl is-active, status, show; service status',
  },
  {
    category: 'Другие утилиты',
    commands: 'ls, awk, wc, tail, head, xargs, grep, sed, echo',
  },
];

export const DISK_USAGE_RULE = `---
# Disk usage check rule
id: node-disk-usage-simple
name: Disk usage check
description: Checks disk usage on root partition
type: node
category: storage
severity: warning
enabled: true
tier: basic

# Rule configuration
config:
  # Execution configuration - directly returns usage percentage
  execution:
    command: "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'"
    timeout: 5

  # Assertions configuration - directly uses command output
  assertions:
    - name: "Disk usage is normal"
      condition: "int(output) < 70"
      severity: warning
      description: "Root partition usage: {{ output }}%"

# Problem resolution recommendations
solution: |
  Handling high disk usage:
  1. Check disk usage: df -h
  2. Find large files: find / -type f -size +100M 2>/dev/null
  3. Check journal usage: journalctl --disk-usage
  4. Contact administrator to clean temporary files and logs (if needed)

# Tags
tags:
  - storage
  - disk
  - usage`;

export const HOST_NETWORK_RULE = `---
# OPA правило - проверка использования сети хоста (упрощённая версия)
id: opa-host-network
name: Проверка использования сети хоста для Pod
description: Проверяет, использует ли Pod сеть хоста; каждое правило — отдельная проверка
type: opa
category: security
severity: warning
enabled: true
tier: basic

# Конфигурация правила
config:
  # Конфигурация ресурсов
  resources:
    - kind: Pod
      apiVersion: v1
      namespaced: true
    - kind: StatefulSet
      apiVersion: apps/v1
      namespaced: true
    - kind: DaemonSet
      apiVersion: apps/v1
      namespaced: true
    - kind: Deployment
      apiVersion: apps/v1
      namespaced: true

  # Конфигурация rego-правила
  rego:
    inline: |
      package kubernetes

      # Получить спецификацию Pod
      get_pod_spec(resource) = spec if {
          resource.kind == "Pod"
          spec := resource.spec
      }

      get_pod_spec(resource) = spec if {
          resource.kind != "Pod"
          spec := resource.spec.template.spec
      }

      # Определение нарушения - использование сети хоста
      violations contains result if {
          resource := input.resources[_]
          spec := get_pod_spec(resource)
          spec.hostNetwork == true

          result := {
              "kind": resource.kind,
              "name": resource.metadata.name,
              "namespace": resource.metadata.namespace,
              "message": sprintf("%s '%s' в пространстве имен '%s' использует сеть хоста", [
                  resource.kind,
                  resource.metadata.name,
                  resource.metadata.namespace
              ])
          }
      }

  # Конфигурация утверждений
  assertions:
    - name: "Проверка использования сети хоста"
      condition: "violation_count == 0"
      severity: warning
      description: "Обнаружено {{ violation_count }} Pod, использующих сеть хоста"

# Рекомендации по устранению проблемы
solution: |
  Обработка рисков использования сети хоста:
  1. Избегайте использования hostNetwork: true, если это не абсолютно необходимо
  2. Используйте Service и Ingress для экспонирования сервисов
  3. Рассмотрите применение плагинов сети CNI для сетевой изоляции

# Метки
tags:
  - security
  - network
  - hostNetwork`;

export const PROHIBITED_COMMANDS = [
  {
    category: 'Файловые операции',
    commands: 'rm, mv, cp (с перезаписью системных файлов), mkdir, rmdir, touch',
  },
  {
    category: 'Права доступа',
    commands: 'chmod, chown, chgrp',
  },
  {
    category: 'Системные сервисы',
    commands:
      'systemctl (start/stop/restart/enable/disable/mask/unmask/kill/reset-failed), service (start/stop/restart)',
  },
  {
    category: 'Системные команды',
    commands: 'init, shutdown, reboot, halt',
  },
  {
    category: 'Управление процессами',
    commands: 'kill, killall, pkill',
  },
  {
    category: 'Дисковые операции',
    commands: 'dd (запись), mkfs, mount, umount, fsck',
  },
  {
    category: 'Управление пакетами',
    commands: 'apt (install/remove/purge/upgrade), apt-get, yum, dnf, pip install, npm install',
  },
  {
    category: 'Сетевые изменения',
    commands:
      'ifconfig (up/down), ip (addr/link/route add/del/set), iptables (-A/-D/-I/-R/-F/-X), netplan apply',
  },
  {
    category: 'Планировщик задач',
    commands: 'crontab (-e/-r), at',
  },
  {
    category: 'Перенаправления вывода',
    commands: '> (перенаправление в файл), >> (добавление в файл)',
  },
  {
    category: 'Скачивание и выполнение',
    commands: 'wget|curl с | sh/bash/python/perl',
  },
  {
    category: 'Удаленное копирование',
    commands: 'scp, rsync',
  },
  {
    category: 'Компиляция и установка',
    commands: 'make (install/clean), ./configure',
  },
  {
    category: 'Параметры ядра',
    commands: 'sysctl -w, echo > /proc/, modprobe, rmmod',
  },
];

export const POD_RESOURCES_RULE = `---
# Правило - проверка наличия ресурсных лимитов у Pod
id: pod-resources-limits
name: Проверка ресурсных лимитов Pod
description: Проверяет, установлены ли ресурсные лимиты (CPU и память) для контейнеров в Pod
type: node
category: resources
severity: warning
enabled: true
tier: basic

# Конфигурация правила
config:
  # Выполнение - проверка через kubectl
  execution:
    command: "kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.spec.containers[] | has("resources") | not) | "(.metadata.namespace)/(.metadata.name)"' | head -10"
    timeout: 10

  # Утверждения
  assertions:
    - name: "Все Pod имеют ресурсные лимиты"
      condition: 'output == ""'
      severity: warning
      # eslint-disable-next-line no-useless-escape
      description: 'Найдено Pod без ресурсных лимитов {{ output }}'

# Рекомендации по устранению
solution: |
  Установка ресурсных лимитов для Pod:
  1. Добавьте resources.limits.cpu и resources.limits.memory в спецификацию контейнеров
  2. Используйте resources.requests для гарантии ресурсов
  3. Пример:
     resources:
       requests:
         memory: "64Mi"
         cpu: "250m"
       limits:
         memory: "128Mi"
         cpu: "500m"

# Метки
tags:
  - resources
  - limits
  - cpu
  - memory`;
