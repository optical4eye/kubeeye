// Constants for Help page content

export const PROHIBITED_COMMANDS = [
  {
    category: "Операции с файлами и директориями",
    commands: "rm, mv, cp (с перезаписью системных файлов), mkdir, rmdir, touch"
  },
  {
    category: "Изменение прав доступа",
    commands: "chmod, chown, chgrp"
  },
  {
    category: "Управление системными сервисами",
    commands: "systemctl (start, stop, restart, enable, disable и т.д.), service (start, stop, restart)"
  },
  {
    category: "Системные операции",
    commands: "init, shutdown, reboot, halt"
  },
  {
    category: "Управление процессами",
    commands: "kill, killall, pkill"
  },
  {
    category: "Низкоуровневые дисковые операции",
    commands: "dd (с записью), mkfs, mount, umount, fsck"
  },
  {
    category: "Управление пакетами",
    commands: "apt (install, remove, upgrade), apt-get, yum, dnf, pip install, npm install"
  },
  {
    category: "Изменение сетевых настроек",
    commands: "ifconfig (up/down), ip (addr/link/route add/del/set), iptables (добавление/удаление правил)"
  },
  {
    category: "Планировщик задач",
    commands: "crontab (редактирование), at"
  },
  {
    category: "Перенаправление вывода",
    commands: `команды с > или >> для записи в файлы`
  },
  {
    category: "Удаленное выполнение и загрузка",
    commands: "wget/curl с выполнением скриптов (wget | sh), scp, rsync"
  },
  {
    category: "Компиляция и установка",
    commands: "make install, ./configure"
  },
  {
    category: "Изменение параметров ядра",
    commands: "sysctl -w, echo в /proc/, modprobe, rmmod"
  }
];

export const SAFE_COMMANDS = [
  {
    category: "Просмотр файлов",
    commands: "cat, less, more, head, tail"
  },
  {
    category: "Поиск и фильтрация",
    commands: "grep, awk, sed, find (только для поиска), locate"
  },
  {
    category: "Информация о системе",
    commands: "uname, hostname, whoami, id, date, uptime"
  },
  {
    category: "Информация о процессах",
    commands: "ps, top, htop, pstree, pgrep"
  },
  {
    category: "Информация о ресурсах",
    commands: "free, vmstat, iostat, sar, df, du, lsblk, lsof"
  },
  {
    category: "Сетевая информация",
    commands: "netstat, ss, iptables -L (просмотр правил)"
  },
  {
    category: "Логи",
    commands: "journalctl (просмотр), dmesg"
  },
  {
    category: "Kubernetes команды",
    commands: "kubectl get, describe, logs (только чтение)"
  }
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