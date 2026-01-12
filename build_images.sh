#!/bin/bash

# Скрипт для сборки Docker-образов KubeEye
# Использование: ./build_images.sh [--frontend] [--backend] [--all] [--version <version>]

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка Docker
if ! command -v docker &> /dev/null; then
    error "Docker не установлен. Пожалуйста, установите Docker перед запуском скрипта."
    exit 1
fi

# Проверка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    warn "Docker Compose не установлен. Некоторые функции могут быть недоступны."
fi

# Флаги сборки
BUILD_FRONTEND=false
BUILD_BACKEND=false
BUILD_ALL=false
VERSION="latest"

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --frontend)
            BUILD_FRONTEND=true
            shift
            ;;
        --backend)
            BUILD_BACKEND=true
            shift
            ;;
        --all)
            BUILD_ALL=true
            shift
            ;;
        --version)
            if [ -n "$2" ]; then
                VERSION="$2"
                shift 2
            else
                error "Укажите версию после --version."
                exit 1
            fi
            ;;
        *)
            error "Неизвестный аргумент: $1"
            exit 1
            ;;
    esac
done

# Если не указаны флаги, собираем все
if ! $BUILD_FRONTEND && ! $BUILD_BACKEND && ! $BUILD_ALL; then
    BUILD_ALL=true
fi

# Функция для сборки фронтенда
build_frontend() {
    log "Сборка Docker-образа для фронтенда с версией $VERSION..."
    cd frontend || exit 1

    # Проверка наличия Dockerfile
    if [ ! -f "Dockerfile" ]; then
        error "Dockerfile для фронтенда не найден."
        exit 1
    fi

    # Сборка образа
    docker build -t kubeeye-frontend:$VERSION .

    if [ $? -eq 0 ]; then
        log "Docker-образ для фронтенда успешно собран: kubeeye-frontend:$VERSION"
    else
        error "Ошибка при сборке Docker-образа для фронтенда."
        exit 1
    fi

    cd ..
}

# Функция для сборки бэкенда
build_backend() {
    log "Сборка Docker-образа для бэкенда с версией $VERSION..."
    cd backend || exit 1

    # Проверка наличия Dockerfile
    if [ ! -f "Dockerfile" ]; then
        error "Dockerfile для бэкенда не найден."
        exit 1
    fi

    # Сборка образа
    docker build -t kubeeye-backend:$VERSION .

    if [ $? -eq 0 ]; then
        log "Docker-образ для бэкенда успешно собран: kubeeye-backend:$VERSION"
    else
        error "Ошибка при сборке Docker-образа для бэкенда."
        exit 1
    fi

    cd ..
}

# Основной процесс сборки
main() {
    log "Начало сборки Docker-образов для KubeEye с версией $VERSION..."

    # Сборка фронтенда
    if [ "$BUILD_ALL" = true ] || [ "$BUILD_FRONTEND" = true ]; then
        build_frontend
    fi

    # Сборка бэкенда
    if [ "$BUILD_ALL" = true ] || [ "$BUILD_BACKEND" = true ]; then
        build_backend
    fi

    log "Сборка Docker-образов завершена успешно!"
}

# Запуск основного процесса
main
