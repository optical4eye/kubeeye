#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main FastAPI application and shared dependencies
"""

# Standard library imports
import os
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

# Third-party imports
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local imports
from .version import VERSION

# Import startup, shutdown and middleware functions
from .startup import (
    _init_database,
    _start_task_manager,
    _start_task_queue,
    _start_cleanup_worker,
    _start_database_monitoring,
    _init_encryption_key,
    _init_websocket_subscriptions,
)
from .shutdown import (
    _shutdown_task_queue,
    _close_ssh_pool,
    _cleanup_services,
    _stop_database_monitoring,
    _close_database_connections,
)
from .unified_middleware import RequestLoggingMiddleware, ValidationMiddleware

# Import route modules
from . import (
    clusters,
    inspection,
    popeye,
    reports,
    scheduled_tasks,
    rules,
    gitops,
    network,
    report_cleanup,
    secrets,
    websocket,
)

# Import new route modules
from .routes import router as routes_router
from .health_endpoints import router as health_router
from .queue_endpoints import router as queue_router
from core.logging import get_logger

logger = get_logger(__name__)


# Constants
DATA_DIR = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
# Only git_rules directory is needed - clusters, results, schedules are in PostgreSQL
GIT_RULES_DIR = DATA_DIR / "git_rules"


# Ensure only necessary directories exist (PostgreSQL is used for clusters, results, schedules)
GIT_RULES_DIR.mkdir(parents=True, exist_ok=True)


# Lifespan context manager for startup and shutdown events - Async Only
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events - Async Only"""
    # Startup
    await _init_database()
    await _start_database_monitoring()
    await _init_encryption_key()
    await _init_websocket_subscriptions()
    await _start_task_queue()
    await _start_cleanup_worker()
    await _start_task_manager()

    yield

    # Shutdown
    await _stop_database_monitoring()
    await _close_database_connections()
    await _shutdown_task_queue()
    await _close_ssh_pool()
    await _cleanup_services()


app = FastAPI(
    title="KubeEye API",
    description="""
    # KubeEye - Kubernetes Cluster Inspection Tool API

    A comprehensive API for inspecting Kubernetes clusters with a focus on security and compliance.

    ## Features

    * **Cluster Management**: Add, configure, and manage multiple Kubernetes clusters
    * **Security Inspections**: Run automated security checks on nodes, pods, and configurations
    * **Rule-based Analysis**: Use customizable rules for compliance checking
    * **Scheduled Inspections**: Automate regular cluster assessments
    * **Report Generation**: Export inspection results in multiple formats (JSON, Excel, PDF)
    * **GitOps Integration**: Manage inspection rules through Git repositories
    * **Real-time Monitoring**: WebSocket support for live inspection progress
    * **Queue Management**: Asynchronous task processing with status tracking

    ## Security

    All operations are read-only and follow strict security guidelines to ensure cluster safety.

    ## Authentication

    Currently uses basic authentication. For production deployments, consider implementing proper authentication mechanisms.

    ## API Endpoints

    ### Core Endpoints
    - `GET /` - API information and available endpoints
    - `GET /api/info` - Detailed API information

    ### Cluster Management
    - `GET /api/dashboard` - Dashboard data
    - `GET /api/clusters` - List all clusters
    - `POST /api/clusters` - Create new cluster
    - `GET /api/clusters/{cluster_name}` - Get cluster details
    - `PUT /api/clusters/{cluster_name}` - Update cluster
    - `DELETE /api/clusters/{cluster_name}` - Delete cluster
    - `GET /api/clusters/{cluster_name}/nodes` - Get cluster nodes
    - `GET /api/clusters/{cluster_name}/namespaces` - Get cluster namespaces
    - `POST /api/clusters/{cluster_name}/test-nodes` - Test node connectivity
    - `POST /api/clusters/{cluster_name}/test-kubeconfig` - Test kubeconfig validity

    ### Inspections
    - `POST /api/inspection` - Run immediate inspection
    - `POST /api/inspection/async` - Run async inspection
    - `GET /api/inspection/task/{task_id}` - Get inspection task status
    - `DELETE /api/inspection/task/{task_id}` - Cancel inspection task

    ### Reports
    - `GET /api/reports` - List inspection reports
    - `GET /api/reports/{report_id}` - Get specific report
    - `DELETE /api/reports/{report_id}` - Delete report
    - `GET /api/reports/{report_id}/export` - Export report in various formats

    ### Scheduled Tasks
    - `GET /api/scheduled-tasks` - List scheduled tasks
    - `POST /api/scheduled-tasks` - Create scheduled task
    - `GET /api/scheduled-tasks/{task_name}` - Get task details
    - `PUT /api/scheduled-tasks/{task_name}` - Update task
    - `DELETE /api/scheduled-tasks/{task_name}` - Delete task
    - `POST /api/scheduled-tasks/{task_name}/run` - Run task immediately

    ### Rules Management
    - `GET /api/rules` - List available rules
    - `GET /api/rules/{rule_type}` - Get rules by type
    - `PUT /api/rules/{rule_type}/{rule_name}` - Update rule configuration

    ### GitOps
    - `GET /api/gitops/config` - Get GitOps configuration
    - `POST /api/gitops/config` - Update GitOps configuration
    - `POST /api/gitops/sync` - Sync rules from Git repository

    ### Network Checks
    - `POST /api/network-check` - Perform network connectivity checks

    ### Report Cleanup
    - `POST /api/cleanup/reports` - Clean up old reports

    ### Secrets Management
    - `GET /api/secrets` - List secrets
    - `POST /api/secrets` - Create secret
    - `GET /api/secrets/{secret_name}` - Get secret details
    - `PUT /api/secrets/{secret_name}` - Update secret
    - `DELETE /api/secrets/{secret_name}` - Delete secret

    ### Health Checks
    - `GET /api/health` - Overall health status
    - `GET /api/health/db` - Database health
    - `GET /api/health/db/monitor` - Database monitoring status
    - `GET /api/health/db/recover` - Database recovery

    ### Queue Management
    - `GET /api/queue/status` - Queue status
    - `GET /api/queue/tasks` - List queued tasks
    - `DELETE /api/queue/tasks/{task_id}` - Cancel queued task

    ### WebSocket
    - `WebSocket /api/ws/{client_id}` - Real-time inspection progress

    ## Documentation

    - **Swagger UI**: `/docs`
    - **ReDoc**: `/redoc`
    - **OpenAPI JSON**: `/openapi.json`
    """,
    version=VERSION,
    contact={
        "name": "KubeEye Team",
        "url": "https://github.com/optical4eye/kubeeye",
        "email": "support@kubeeye.io",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Add validation middleware (exclude /api/secrets and /api/clusters from body validation as they contain secret variables)
app.add_middleware(ValidationMiddleware, max_query_length=1000, exclude_paths=["/api/secrets", "/api/clusters"])

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify concrete origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and include all route modules

app.include_router(routes_router)
app.include_router(health_router)
app.include_router(queue_router)
app.include_router(websocket.router)

app.include_router(clusters.router, prefix="/api", tags=["clusters"])
app.include_router(inspection.router, prefix="/api", tags=["inspection"])
app.include_router(popeye.router, prefix="/api", tags=["popeye"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(scheduled_tasks.router, prefix="/api", tags=["scheduled-tasks"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(gitops.router, prefix="/api", tags=["gitops"])
app.include_router(network.router, prefix="/api", tags=["network"])
app.include_router(report_cleanup.router, prefix="/api", tags=["report-cleanup"])
app.include_router(secrets.router, prefix="/api", tags=["secrets"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
