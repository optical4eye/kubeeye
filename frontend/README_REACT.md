# KubeEye с React UI

Это обновленная версия KubeEye с современным React frontend вместо Streamlit.

## Архитектура

- **Backend**: FastAPI (Python) - REST API
- **Frontend**: React + Ant Design - веб-интерфейс
- **База данных**: Файловая система (JSON файлы)

## Запуск

### Локальный запуск

1. **Установка зависимостей backend:**
```bash
pip install -r requirements.txt
```

2. **Установка зависимостей frontend:**
```bash
cd frontend
npm install
```

3. **Сборка React приложения:**
```bash
npm run build
cd ..
```

4. **Запуск backend:**
```bash
python api.py
```

Frontend будет доступен на http://localhost:8000, API на http://localhost:8000/api/

### Docker

```bash
docker build -t kubeeye:v3.0 .
docker run -p 80:80 kubeeye:v3.0
```

Приложение будет доступно на http://localhost

### Kubernetes (Helm)

```bash
helm install kubeeye ./chart/kubeeye
```

## API Endpoints

- `GET /api/dashboard` - данные dashboard
- `GET /api/clusters` - список кластеров
- `POST /api/clusters` - создать кластер
- `DELETE /api/clusters/{name}` - удалить кластер
- `POST /api/inspection` - запустить инспекцию
- `GET /api/reports` - список отчетов
- `GET /api/rules` - правила инспекции

## Структура проекта

```
kubeeye/
├── api.py                 # FastAPI backend
├── frontend/              # React приложение
│   ├── src/
│   │   ├── components/    # React компоненты
│   │   ├── pages/         # Страницы
│   │   └── services/      # API сервисы
│   └── public/
├── chart/                 # Helm chart
├── Dockerfile             # Многостадийная сборка
├── docker-entrypoint.sh   # Скрипт запуска
└── requirements.txt       # Python зависимости
```

## Миграция с Streamlit

Проект полностью переведен с Streamlit на React:

1. **UI**: Streamlit заменен на React + Ant Design
2. **API**: Добавлен FastAPI слой для всех операций
3. **Архитектура**: Разделение frontend/backend
4. **Docker**: Многостадийная сборка (Node.js + Python)
5. **Helm**: Обновлен для работы с nginx + FastAPI

## Функциональность

- ✅ Dashboard с метриками и графиками
- ✅ Управление кластерами (добавление, редактирование, удаление)
- ✅ Немедленная инспекция кластеров
- ✅ Просмотр и управление отчетами
- ✅ Экспорт отчетов (JSON, Excel, PDF)
- ✅ Управление правилами инспекции

## Разработка

### Backend (FastAPI)
```bash
# Запуск в режиме разработки
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React)
```bash
cd frontend
npm start
```

Frontend будет доступен на http://localhost:3000 с прокси на API.

## Тестирование

1. Запустите backend: `python api.py`
2. В другом терминале: `cd frontend && npm start`
3. Откройте http://localhost:3000
4. Проверьте функциональность через UI