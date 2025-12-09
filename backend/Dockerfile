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

# Download corresponding OPA binary file based on target architecture
RUN set -eux; \
    OPA_VERSION="v1.11.0"; \
    case "${TARGETARCH:-amd64}" in \
        amd64) \
            OPA_ARCH="amd64"; \
            ;; \
        arm64) \
            OPA_ARCH="arm64"; \
            ;; \
        arm) \
            OPA_ARCH="arm"; \
            ;; \
        *) \
            echo "Unsupported architecture: ${TARGETARCH}"; \
            exit 1; \
            ;; \
    esac; \
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
RUN chown -R kubeeye:kubeeye /app

USER kubeeye

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Start FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]