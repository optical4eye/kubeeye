# Builder stage for dependencies
FROM python:3.14-alpine AS builder

ARG OPA_VERSION=v1.12.2
ARG POPEYE_VERSION=v0.22.1

# Set environment variables
ENV UV_CACHE_DIR=/tmp/uv-cache

# Install build dependencies
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    openssh-client \
    curl \
    libgit2-dev \
    font-dejavu \
    font-liberation \
    tzdata

# Download OPA and Popeye binaries
RUN set -eux; \
    ARCH=$(uname -m); \
    case "${ARCH}" in \
        x86_64) RELEASE_ARCH="amd64" ;; \
        aarch64) RELEASE_ARCH="arm64" ;; \
        arm*) RELEASE_ARCH="arm" ;; \
        *) echo "Unsupported architecture: ${ARCH}"; exit 1 ;; \
    esac; \
    curl -sSL "https://github.com/open-policy-agent/opa/releases/download/${OPA_VERSION}/opa_linux_${RELEASE_ARCH}_static" -o opa && \
    chmod +x opa && \
    mv opa /usr/local/bin/opa; \
    curl -L "https://github.com/derailed/popeye/releases/download/${POPEYE_VERSION}/popeye_linux_${RELEASE_ARCH}.tar.gz" -o popeye.tar.gz && \
    tar -xzf popeye.tar.gz && \
    chmod +x popeye && \
    mv popeye /usr/local/bin/popeye && \
    rm popeye.tar.gz

# Set working directory
WORKDIR /app

# Create virtual environment and install dependencies
COPY requirements.txt /app/

RUN pip install --no-cache-dir uv && \
    uv venv /app/venv && \
    uv pip install --python /app/venv/bin/python --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.14-alpine

# Set environment variables
ENV PYTHONPATH=/app \
    KUBEEYE_DATA_DIR=/app/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/venv/bin:$PATH"

# Install only runtime dependencies
RUN apk update && apk add --no-cache \
    openssh-client \
    curl \
    libssl3 \
    libgit2 \
    font-dejavu \
    font-liberation \
    tzdata

# Add user for security
RUN addgroup -S kubeeye --gid 1001 && adduser -u 1001 -S kubeeye -G kubeeye

# Copy virtual environment from builder
COPY --from=builder --chown=kubeeye:kubeeye /app/venv /app/venv

# Copy binaries from builder
COPY --from=builder --chown=kubeeye:kubeeye /usr/local/bin/opa /usr/local/bin/opa
COPY --from=builder --chown=kubeeye:kubeeye /usr/local/bin/popeye /usr/local/bin/popeye

# Copy application code
COPY --chown=kubeeye:kubeeye app /app/

# Set working directory
WORKDIR /app

# Switch to non-root user
USER kubeeye

# Expose port
EXPOSE 8000

# Improved health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f --max-time 10 --silent --output /dev/null http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "scripts.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--log-level", "critical"]