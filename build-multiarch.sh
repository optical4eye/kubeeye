#!/bin/bash

# KubeEye multi-architecture image build script
# Support for amd64, arm64, arm/v7 architectures

set -e

# Variable setup
IMAGE_NAME="${IMAGE_NAME:-kubeeye}"
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-}"

# If REGISTRY variable is set, add prefix
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}"
fi

echo "Starting multi-architecture image build: ${FULL_IMAGE_NAME}:${TAG}"

# Check Docker buildx availability
if ! docker buildx version > /dev/null 2>&1; then
    echo "Docker buildx is not available, ensure Docker version supports buildx"
    exit 1
fi

# Create buildx builder if it doesn't exist
BUILDER_NAME="kubeeye-multiarch"
if ! docker buildx ls | grep -q $BUILDER_NAME; then
    echo "Creating multi-architecture builder..."
    docker buildx create --name $BUILDER_NAME --use
else
    echo "Using existing builder: $BUILDER_NAME"
    docker buildx use $BUILDER_NAME
fi

# Enable binfmt_misc support for cross-compilation
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

echo "Building for supported architectures: linux/amd64, linux/arm64"

# Build and publish multi-architecture image
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag "${FULL_IMAGE_NAME}:${TAG}" \
    --tag "${FULL_IMAGE_NAME}:latest" \
    --push \
    .

echo "Multi-architecture image build completed!"
echo "Image tag: ${FULL_IMAGE_NAME}:${TAG}"
echo "Image tag: ${FULL_IMAGE_NAME}:latest"

# Show image information
echo ""
echo "Detailed image information:"
docker buildx imagetools inspect "${FULL_IMAGE_NAME}:${TAG}"
