# Backend KubeEye

Backend KubeEye - это серверная часть приложения, отвечающая за обработку запросов, инспекцию кластеров Kubernetes и предоставление API для фронтенда. Backend написан на Python с использованием фреймворка FastAPI.

## Структура проекта

```
backend/
├── app/                          # Основное приложение
│   ├── api/                      # API контроллеры
│   ├── services/                 # Бизнес-логика
│   ├── infrastructure/           # Инфраструктурные компоненты
│   └── scripts/                  # Исполняемые скрипты
├── tests/                        # Тесты
├── Dockerfile                    # Docker конфигурация
├── requirements.txt              # Зависимости Python
└── README.md                     # Документация
```

## Основные компоненты

### API контроллеры
- **`main.py`**: Главный контроллер FastAPI.
- **`clusters.py`**: Управление кластерами.
- **`inspection.py`**: Инспекции кластеров.
- **`reports.py`**: Генерация и управление отчетами.
- **`rules.py`**: Управление правилами инспекции.

### Сервисы
- **`inspectors/`**: Логика инспекции Kubernetes.
- **`components/`**: Дополнительные компоненты бизнес-логики.

### Инфраструктура
- **`cluster/`**: Утилиты для работы с Kubernetes.
- **`security/`**: Безопасность и шифрование.
- **`logging/`**: Логирование.
- **`network/`**: Сетевые проверки.

## Запуск

### Локальный запуск
```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите сервер
python -m backend.app.scripts.api
```

### Docker
```bash
# Соберите образ
docker build -t kubeeye-backend .

# Запустите контейнер
docker run -p 8000:8000 kubeeye-backend
```

## Тестирование

Для запуска тестов используйте:
```bash
# Запуск всех тестов
./run_test.sh

# Запуск unit тестов
./run_test.sh --unit

# Запуск интеграционных тестов
./run_test.sh --integration
```

## Конфигурация

Основные переменные окружения:

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `PYTHONPATH` | `/app` | Путь поиска модулей Python |
| `KUBEEYE_DATA_DIR` | `/app/data` | Директория для хранения данных приложения (кластеры, отчеты и т.д.) |
| `KUBEEYE_REPORT_RETENTION_DAYS` | `1` | Количество дней хранения отчетов инспекции перед очисткой |
| `KUBEEYE_SSH_CONNECTION_TIMEOUT` | `10` | Базовый таймаут для SSH соединений в секундах. Влияет на все SSH-таймауты пропорционально |
| `KUBEEYE_SSH_MAX_CONCURRENT_CHECKS` | `10` | Максимальное количество одновременных проверок SSH соединений во время инспекции |
| `KUBEEYE_GITOPS_REPO_NAME` | `kubeeye_rules` | Идентификатор имени для репозитория правил GitOps |
| `KUBEEYE_GITOPS_REPO_URL` | `https://github.com/optical4eye/kubeeye-rules.git` | URL репозитория правил GitOps |
| `KUBEEYE_GITOPS_REPO_BRANCH` | `main` | Ветка репозитория правил GitOps для использования |
| `KUBEEYE_GITOPS_REPO_USERNAME` | `optical4eye` | Имя пользователя для аутентификации в репозитории GitOps |
| `KUBEEYE_GITOPS_REPO_TOKEN` | `""` | Персональный токен доступа для репозитория GitOps |
| `KUBEEYE_GITOPS_REPO_DESCRIPTION` | `kubeeye repo rules` | Описание репозитория правил GitOps |

## Безопасность

Backend KubeEye обеспечивает безопасность за счет:
- **Политики только для чтения**: Все операции инспекции ограничены сбором информации.
- **Шифрование данных**: Чувствительная информация шифруется.
- **Валидация запросов**: Все входящие запросы проходят строгую валидацию.
