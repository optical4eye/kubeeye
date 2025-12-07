#!/bin/bash

# Скрипт сборки мультиархитектурного образа KubeEye
# Поддержка архитектур amd64, arm64, arm/v7

set -e

# Настройка переменных
IMAGE_NAME="${IMAGE_NAME:-kubeeye}"
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-}"

# Если переменная REGISTRY установлена, добавить префикс
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}"
fi

echo "Начинается сборка мультиархитектурного образа: ${FULL_IMAGE_NAME}:${TAG}"

# Проверка доступности Docker buildx
if ! docker buildx version > /dev/null 2>&1; then
    echo "Docker buildx недоступен, убедитесь, что версия Docker поддерживает buildx"
    exit 1
fi

# Создание buildx билдера, если он не существует
BUILDER_NAME="kubeeye-multiarch"
if ! docker buildx ls | grep -q $BUILDER_NAME; then
    echo "Создание мультиархитектурного билдера..."
    docker buildx create --name $BUILDER_NAME --use
else
    echo "Использование существующего билдера: $BUILDER_NAME"
    docker buildx use $BUILDER_NAME
fi

# Включение поддержки binfmt_misc для кросс-компиляции
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

echo "Сборка для поддерживаемых архитектур: linux/amd64, linux/arm64"

# Сборка и публикация мультиархитектурного образа
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag "${FULL_IMAGE_NAME}:${TAG}" \
    --tag "${FULL_IMAGE_NAME}:latest" \
    --push \
    .

echo "Сборка мультиархитектурного образа завершена!"
echo "Тег образа: ${FULL_IMAGE_NAME}:${TAG}"
echo "Тег образа: ${FULL_IMAGE_NAME}:latest"

# Показать информацию об образе
echo ""
echo "Подробная информация об образе:"
docker buildx imagetools inspect "${FULL_IMAGE_NAME}:${TAG}"
