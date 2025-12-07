FROM python:3.13-alpine


LABEL maintainer="KubeSphere Team"
LABEL description="KubeEye Kubernetes Cluster Inspection Tool"
LABEL version="2.0.0"


# [translate:设置构建参数以支持多架构]  # Установить параметры сборки для поддержки нескольких архитектур
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH


# [translate:设置工作目录]  # Установить рабочую директорию
WORKDIR /app


# [translate:安装系统依赖]  # Установить системные зависимости
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


# [translate:首先复制requirements.txt以利用Docker缓存]  # Сначала скопировать requirements.txt, чтобы использовать кэш Docker
COPY requirements.txt /app/


# [translate:安装Python依赖]  # Установить зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# [translate:设置环境变量]  # Установить переменные окружения
ENV PYTHONPATH=/app
ENV KUBEEYE_DATA_DIR=/app/data
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false


# [translate:根据目标架构下载对应的OPA二进制文件]  # Скачать подходящий бинарник OPA в зависимости от целевой архитектуры
RUN set -eux; \
    OPA_VERSION="v1.10.1"; \
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

# [translate:复制项目文件]  # Копировать файлы проекта
COPY . /app/

# [translate:创建数据目录并设置权限]  # Создать каталоги данных и установить права доступа
RUN mkdir -p /app/data/clusters /app/data/results /app/data/logs /app/data/schedules /app/data/git_rules

# [translate:初始化应用（在切换用户前执行）]  # Инициализировать приложение (выполнить до смены пользователя)
RUN python init.py

# Add user
RUN addgroup -S kubeeye --gid 1001 && adduser -u 1001 -S kubeeye -G kubeeye

RUN chown -R kubeeye:kubeeye /app

USER kubeeye

# [translate:暴露服务端口]  # Открыть порт сервиса
EXPOSE 8501


# [translate:健康检查]  # Проверка состояния
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1


# [translate:启动应用]  # Запустить приложение
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
