# Backend Dockerfile - FastAPI application
FROM python:3.13-alpine

# Install system dependencies
RUN apk update && \
    apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    openssh-client \
    curl \
    git \
    font-dejavu \
    font-liberation

# Set working directory
WORKDIR /app

# First copy requirements.txt to utilize Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONPATH=/app
ENV KUBEEYE_DATA_DIR=/app/data

# Download OPA binary for the correct architecture
RUN set -eux; \
    # Determine architecture using uname
    ARCH=$(uname -m); \
    case "${ARCH}" in \
        x86_64) \
            OPA_ARCH="amd64"; \
            ;; \
        aarch64) \
            OPA_ARCH="arm64"; \
            ;; \
        arm*) \
            OPA_ARCH="arm"; \
            ;; \
        *) \
            echo "Unsupported architecture: ${ARCH}"; \
            exit 1; \
            ;; \
    esac; \
    echo "Detected architecture: ${ARCH}, using OPA arch: ${OPA_ARCH}"; \
    OPA_VERSION="v1.11.0"; \
    curl -sSL "https://github.com/open-policy-agent/opa/releases/download/${OPA_VERSION}/opa_linux_${OPA_ARCH}_static" -o opa && \
    chmod +x opa && \
    mv opa /usr/local/bin/opa

# Copy project files
COPY . /app/


# Create data directories
RUN mkdir -p /app/data/clusters /app/data/results /app/data/logs /app/data/schedules /app/data/git_rules

# Initialize application
RUN python init.py

# Add user for security
RUN addgroup -S kubeeye --gid 1001 && adduser -u 1001 -S kubeeye -G kubeeye
RUN chown -R kubeeye:kubeeye /app /usr/local/bin/opa

USER kubeeye

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Start FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]