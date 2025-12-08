FROM python:3.13-alpine


LABEL maintainer="KubeSphere Team"
LABEL description="KubeEye Kubernetes Cluster Inspection Tool"
LABEL version="2.0.0"

# Set build parameters to support multi-architecture
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    openssh-client \
    curl \
    git \
    font-dejavu \
    font-liberation \
    && apk upgrade --no-cache

# First copy requirements.txt to utilize Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONPATH=/app
ENV KUBEEYE_DATA_DIR=/app/data
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Download corresponding OPA binary file based on target architecture
RUN set -eux; \
    OPA_VERSION="v1.11.0"; \
    case "${TARGETARCH}" in \
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

# Create data directories and set permissions
RUN mkdir -p /app/data/clusters /app/data/results /app/data/logs /app/data/schedules /app/data/git_rules

# Initialize application (execute before switching user)
RUN python init.py

# Add user
RUN addgroup -S kubeeye --gid 1001 && adduser -u 1001 -S kubeeye -G kubeeye

RUN chown -R kubeeye:kubeeye /app

USER kubeeye

# Expose service port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start application
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
