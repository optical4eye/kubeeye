# KubeEye Helm Chart

Helm чарт для развертывания KubeEye - инструмента инспекции безопасности Kubernetes кластеров.

## Обзор

KubeEye предоставляет комплексное решение для:
- Инспекции безопасности кластеров Kubernetes
- Управления правилами безопасности через GitOps
- Мониторинга сетевой связности
- Генерации отчетов о соответствии требованиям

Чарт включает в себя:
- Backend API сервер (FastAPI + PostgreSQL)
- Frontend веб-интерфейс (React)
- PostgreSQL базу данных
- Набор встроенных правил безопасности

## Архитектура

```
kubeeye-frontend (React)
         |
         v
kubeeye-backend (FastAPI)
         |
         v
kubeeye-postgresql (PostgreSQL)
```

## Установка

### Предварительные требования

- Kubernetes 1.19+
- Helm 3.0+
- Доступ к Docker registry с образами KubeEye

### Добавление репозитория

```bash
# Если чарт размещен в репозитории
helm repo add kubeeye https://your-repo-url
helm repo update
```

### Установка чарта

```bash
# Установка с дефолтными параметрами
helm install kubeeye ./chart/kubeeye

# Установка в определенный namespace
helm install kubeeye ./chart/kubeeye -n kubeeye-system --create-namespace

# Установка с кастомными values
helm install kubeeye ./chart/kubeeye -f my-values.yaml
```

### Обновление

```bash
helm upgrade kubeeye ./chart/kubeeye
```

### Удаление

```bash
helm uninstall kubeeye
```

## Конфигурация

### Основные параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `frontend.replicaCount` | Количество реплик frontend | `1` |
| `backend.replicaCount` | Количество реплик backend | `1` |
| `postgresql.enabled` | Включить PostgreSQL | `true` |
| `postgresql.primary.persistence.size` | Размер диска PostgreSQL | `8Gi` |
| `externalSecret.enabled` | Использовать ExternalSecret | `false` |

### Frontend параметры

```yaml
frontend:
  replicaCount: 1
  image:
    repository: kubeeye-frontend
    tag: "v3.3"
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  resources:
    limits:
      memory: "1Gi"
      cpu: "500m"
    requests:
      memory: "1Gi"
      cpu: "500m"
```

### Backend параметры

```yaml
backend:
  replicaCount: 1
  image:
    repository: kubeeye-backend
    tag: "v3.3"
    pullPolicy: IfNotPresent
  service:
    port: 8000
  env:
    - name: KUBEEYE_LOG_LEVEL
      value: "INFO"
    - name: KUBEEYE_REPORT_RETENTION_DAYS
      value: "7"
  resources:
    limits:
      memory: "2Gi"
      cpu: "1000m"
    requests:
      memory: "2Gi"
      cpu: "1000m"
```

### PostgreSQL параметры

```yaml
postgresql:
  enabled: true
  image:
    registry: docker.io
    repository: postgres
    tag: 18-alpine
  auth:
    username: "kubeeye"
    password: "password"
    database: "kubeeye-db"
  primary:
    persistence:
      enabled: true
      size: 8Gi
```

### ExternalSecret параметры

```yaml
externalSecret:
  enabled: false
  clusterSecretStoreName: "vault-backend"
  secrets:
    - secretName: "gitUser"
      vaultPath: "git/creds"
      vaultKey: "username"
    - secretName: "gitToken"
      vaultPath: "git/creds"
      vaultKey: "token"
    - secretName: "kubeeye-postgres-secret"
      vaultPath: "database/postgres"
      vaultKey: "password"
```

## Переменные окружения Backend

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `PYTHONPATH` | Путь поиска модулей Python | `/app` |
| `KUBEEYE_DATA_DIR` | Директория для хранения данных приложения (кластеры, отчеты и т.д.) | `/app/data` |
| `KUBEEYE_DB_HOST` | Хост PostgreSQL | `kubeeye-postgresql` |
| `KUBEEYE_DB_PORT` | Порт PostgreSQL | `5432` |
| `KUBEEYE_DB_USER` | Пользователь БД | `kubeeye` |
| `KUBEEYE_DB_PASS` | Пароль БД | `password` |
| `KUBEEYE_DB_NAME` | Имя БД | `kubeeye-db` |
| `KUBEEYE_SQL_DEBUG` | Включить SQL debug логирование | `False` |
| `KUBEEYE_LOG_LEVEL` | Уровень логирования | `INFO` |
| `KUBEEYE_REPORT_RETENTION_DAYS` | Дни хранения отчетов | `7` |
| `KUBEEYE_SSH_CONNECTION_TIMEOUT` | Таймаут SSH соединения (секунды) | `10` |
| `KUBEEYE_SSH_MAX_CONCURRENT_CHECKS` | Максимальное количество одновременных SSH проверок | `20` |
| `KUBEEYE_SSH_COMMAND_TIMEOUT` | Таймаут выполнения SSH команды (секунды) | `30` |
| `KUBEEYE_SSH_RETRY_ATTEMPTS` | Количество повторных попыток SSH соединения | `2` |
| `KUBEEYE_SSH_RETRY_DELAY` | Задержка между повторными попытками (секунды) | `1` |
| `KUBEEYE_SSH_POOL_ENABLED` | Включить пул SSH соединений | `true` |
| `KUBEEYE_SSH_POOL_SIZE` | Размер пула SSH соединений | `10` |
| `KUBEEYE_SSH_POOL_CONNECTION_TIMEOUT` | Таймаут соединения в пуле SSH (секунды, 5 минут) | `300` |
| `KUBEEYE_SSH_POOL_KEEPALIVE_INTERVAL` | Интервал keepalive для пула SSH (секунды, 1 минута) | `60` |
| `KUBEEYE_SSH_KEEP_ALIVE` | Поддерживать SSH соединения активными | `true` |
| `KUBEEYE_SSH_VERBOSE` | Подробное логирование SSH | `false` |
| `KUBEEYE_SSH_LOG_OUTPUT` | Логировать вывод SSH команд | `false` |
| `KUBEEYE_GITOPS_REPO_NAME` | Идентификатор репозитория правил GitOps | `kubeeye_rules` |
| `KUBEEYE_GITOPS_REPO_URL` | URL репозитория правил | `https://github.com/optical4eye/kubeeye-rules.git` |
| `KUBEEYE_GITOPS_REPO_BRANCH` | Ветка репозитория | `main` |
| `KUBEEYE_GITOPS_REPO_USERNAME` | Пользователь GitOps | `optical4eye` |
| `KUBEEYE_GITOPS_REPO_TOKEN` | Токен GitOps | `""` |
| `KUBEEYE_GITOPS_REPO_DESCRIPTION` | Описание репозитория правил GitOps | `kubeeye repo rules` |
| `KUBEEYE_GITOPS_SYNC_INTERVAL` | Интервал синхронизации GitOps в секундах (по умолчанию: 5 минут) | `300` |
| `GIT_SSL_NO_VERIFY` | Отключает проверку SSL сертификатов в Git | `None` |
| `KUBEEYE_POPEYE_PATH` | Путь к исполняемому файлу Popeye | `/usr/local/bin/popeye` |
| `KUBEEYE_POPEYE_TIMEOUT` | Таймаут выполнения сканирования Popeye (секунды) | `300` |
| `KUBEEYE_POPEYE_DEFAULT_FORMAT` | Формат вывода для Popeye | `html` |
| `KUBEEYE_JWT_SECRET_KEY` | Секретный ключ для подписи JWT токенов (обязательно изменить в production) | `your-secret-key-change-in-production` |
| `KUBEEYE_JWT_ALGORITHM` | Алгоритм шифрования JWT токенов | `HS256` |
| `KUBEEYE_JWT_ACCESS_TOKEN_EXPIRE_HOURS` | Срок действия access токена в часах | `24` |
| `KUBEEYE_ADMIN_USERNAME` | Имя пользователя администратора | `admin` |
| `KUBEEYE_ADMIN_EMAIL` | Email администратора | `admin@kubeeye.local` |
| `KUBEEYE_ADMIN_PASSWORD` | Пароль администратора (обязательно изменить в production) | `admin123` |
| `KUBEEYE_MAX_FAILED_LOGIN_ATTEMPTS` | Максимальное количество неудачных попыток входа перед блокировкой | `5` |
| `KUBEEYE_ACCOUNT_LOCK_DURATION_MINUTES` | Длительность блокировки аккаунта в минутах | `30` |
| `KUBEEYE_AUDIT_ENABLED` | Включить/отключить логирование аудита | `True` |
| `KUBEEYE_AUDIT_RETENTION_DAYS` | Количество дней хранения логов аудита | `14` |
| `KUBEEYE_OAUTH_ENABLED` | Включить/отключить OAuth аутентификацию | `True` |
| `KUBEEYE_OAUTH_ISSUER_URL` | URL Dex OIDC issuer | `http://dex:5556` |
| `KUBEEYE_OAUTH_CLIENT_ID` | Client ID для OIDC | `kubeeye` |
| `KUBEEYE_OAUTH_CLIENT_SECRET` | Client Secret для OIDC | `kubeeye-secret` |
| `KUBEEYE_OAUTH_REDIRECT_URI` | URI для callback после аутентификации | `http://localhost:3000/auth/callback` |
| `KUBEEYE_OAUTH_ADMIN_GROUPS` | Список групп для роли admin (через запятую) | `kubeeye-admins` |
| `KUBEEYE_OAUTH_OPERATOR_GROUPS` | Список групп для роли operator (через запятую) | `kubeeye-operators` |
| `KUBEEYE_OAUTH_SCOPES` | Запрашиваемые OIDC scopes | `openid,profile,email,groups` |

## Аутентификация через Dex (OAuth/OIDC)

KubeEye использует Dex как OIDC провайдер для аутентификации пользователей. Dex может подключаться к различным identity provider (LDAP, Active Directory, GitHub, Google и др.).

### Архитектура аутентификации

```
User → Frontend → Backend → Dex → LDAP/AD/Other IdP
                ↓
           JWT Token
```

### Конфигурация Dex

Создайте ConfigMap с конфигурацией Dex:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dex-config
data:
  config.yaml: |
    issuer: https://dex.your-domain.com
    storage:
      type: kubernetes
      config:
        inCluster: true
    web:
      http: 0.0.0.0:5556

    staticClients:
      - id: kubeeye
        redirectURIs:
          - 'https://kubeeye.your-domain.com/auth/callback'
        name: 'KubeEye'
        secret: your-client-secret

    connectors:
      - type: ldap
        id: ldap
        name: OpenLDAP
        config:
          host: ldap.your-domain.com:636
          rootCAData: <base64-encoded-ca>
          bindDN: cn=admin,dc=example,dc=com
          bindPW: $LDAP_BIND_PASSWORD
          usernamePrompt: Username
          userSearch:
            baseDN: ou=users,dc=example,dc=com
            filter: '(objectClass=person)'
            username: uid
            idAttr: DN
            emailAttr: mail
            nameAttr: cn
            groupsAttr: memberOf
          groupSearch:
            baseDN: ou=groups,dc=example,dc=com
            filter: '(objectClass=groupOfNames)'
            userMatchers:
              - userAttr: DN
                groupAttr: member
            nameAttr: cn
```

### Настройка переменных окружения для OAuth

```yaml
backend:
  env:
    - name: KUBEEYE_OAUTH_ENABLED
      value: "true"
    - name: KUBEEYE_OAUTH_ISSUER_URL
      value: "https://dex.your-domain.com"
    - name: KUBEEYE_OAUTH_CLIENT_ID
      value: "kubeeye"
    - name: KUBEEYE_OAUTH_CLIENT_SECRET
      valueFrom:
        secretKeyRef:
          name: kubeeye-oauth-secret
          key: client-secret
    - name: KUBEEYE_OAUTH_REDIRECT_URI
      value: "https://kubeeye.your-domain.com/auth/callback"
    - name: KUBEEYE_OAUTH_ADMIN_GROUPS
      value: "kubeeye-admins,k8s-admins,infra-admins"
    - name: KUBEEYE_OAUTH_OPERATOR_GROUPS
      value: "kubeeye-operators,k8s-operators"
```

### Fallback аутентификация

Локальный admin пользователь всегда доступен как fallback при неработающем OAuth:
- Username: `admin` (из `KUBEEYE_ADMIN_USERNAME`)
- Password: из `KUBEEYE_ADMIN_PASSWORD`

## Правила безопасности

Чарт включает встроенные правила инспекции:

### Node правила
- `node-disk-usage-simple`: Проверка использования диска

### OPA правила
- `opa-host-network`: Проверка host network политик

Правила хранятся в `rules/` директории и автоматически загружаются при запуске.

## Мониторинг

### Health Checks

- Frontend: HTTP health check на `/`
- Backend: HTTP health check на `/health`
- PostgreSQL: Readiness probe через `pg_isready`

### Логирование

Все компоненты используют структурированное JSON логирование с уровнем, настраиваемым через `KUBEEYE_LOG_LEVEL`.

## Безопасность

### Security Context

По умолчанию включены restrictive security contexts:
- `allowPrivilegeEscalation: false`
- `runAsNonRoot: true`
- `capabilities: drop: [ALL]`
- `seccompProfile: type: RuntimeDefault`

### Network Policies

PostgreSQL имеет встроенные Network Policies для ограничения трафика.

### External Secrets

Поддержка интеграции с внешними secret managers (Vault, AWS Secrets Manager) через ExternalSecret.

## Резервное копирование

### PostgreSQL

- Persistence включена по умолчанию
- Используйте стандартные инструменты PostgreSQL для бэкапа
- Рекомендуется настроить регулярные бэкапы через cron jobs

### Данные приложений

- Отчеты и результаты инспекций хранятся в PostgreSQL
- Настраиваемый период хранения через `KUBEEYE_REPORT_RETENTION_DAYS`

## Troubleshooting

### Общие проблемы

1. **Не удается подключиться к PostgreSQL**
   - Проверьте статус pod'а: `kubectl get pods -n kubeeye-system`
   - Проверьте логи: `kubectl logs -n kubeeye-system kubeeye-postgresql-0`

2. **Frontend не загружается**
   - Проверьте сервис: `kubectl get svc -n kubeeye-system`
   - Проверьте ingress (если используется)

3. **Инспекции не работают**
   - Проверьте подключение к кластеру в backend логах
   - Убедитесь, что service account имеет необходимые права

### Логи

```bash
# Логи backend
kubectl logs -n kubeeye-system deployment/kubeeye-backend

# Логи frontend
kubectl logs -n kubeeye-system deployment/kubeeye-frontend

# Логи PostgreSQL
kubectl logs -n kubeeye-system kubeeye-postgresql-0
```

## Разработка

### Структура чарта

```
chart/kubeeye/
├── Chart.yaml          # Метаданные чарта
├── values.yaml         # Дефолтные значения
├── Chart.lock          # Lock файл зависимостей
├── templates/          # Kubernetes манифесты
│   ├── deployment.yaml # Deployments для frontend/backend
│   ├── service.yaml    # Services
│   ├── configmap.yaml  # ConfigMaps для правил
│   ├── pvc.yaml        # PersistentVolumeClaims
│   └── external-secrets.yaml # ExternalSecret ресурсы
├── rules/              # Правила инспекции
└── charts/             # Зависимости (PostgreSQL)
```

### Кастомизация

1. **Добавление новых правил**: Поместите YAML файлы в `rules/`
2. **Кастомизация образов**: Измените `image.repository` и `image.tag`
3. **Добавление environment переменных**: Добавьте в `backend.env` или `frontend.env`

## Версии

- **Chart version**: 3.3.0
- **App version**: v3.3
- **PostgreSQL**: 18.2.0 (Bitnami)

## Поддержка

Для вопросов и проблем:
- Создайте issue в репозитории проекта
- Проверьте логи приложений
- Убедитесь, что все предварительные требования выполнены