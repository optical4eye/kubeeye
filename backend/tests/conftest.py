#!/usr/bin/env python3
# pytest fixtures for KubeEye backend tests

# Performance optimization: use uvloop for better asyncio performance in tests
try:
    import uvloop
    import asyncio
    import warnings

    # Suppress deprecation warning for asyncio.set_event_loop_policy in Python 3.14+
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass  # uvloop not available, use default asyncio

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from db.database_connection_manager import Base


@pytest.fixture
def temp_data_dir():
    """Temporary directory for test data"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_env_vars(temp_data_dir):
    """Mock environment variables for testing"""
    env_vars = {
        "KUBEEYE_DATA_DIR": str(temp_data_dir),
        "KUBEEYE_REPORT_RETENTION_DAYS": "7",
        "KUBEEYE_SSH_CONNECTION_TIMEOUT": "10",
        "KUBEEYE_SSH_MAX_CONCURRENT_CHECKS": "50",  # Support for 50 hosts
        "PYTHONPATH": "/app",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_USER": "kubeeye",
        "DB_PASS": "kubeeye",
        "DB_NAME": "kubeeye-db-test",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def sample_cluster_data():
    """Sample cluster configuration for testing"""
    return {
        "name": "test-cluster",
        "api_server": "https://test-cluster.example.com:6443",
        "token": "test-token-12345",
        "ca_cert": "LS0tLS1CRUdJTi...",
        "namespace": "default",
    }


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes API client"""
    mock_client = Mock()
    mock_client.list_namespaced_pod.return_value = Mock(items=[])
    mock_client.list_namespaced_service.return_value = Mock(items=[])
    mock_client.list_namespaced_deployment.return_value = Mock(items=[])
    return mock_client


@pytest.fixture
def mock_ssh_connection():
    """Mock SSH connection for node testing"""
    mock_ssh = Mock()
    mock_ssh.connect.return_value = None
    mock_ssh.close.return_value = None
    mock_ssh.exec_command.return_value = (Mock(), Mock(), Mock())
    return mock_ssh


@pytest.fixture
def mock_asyncssh_connection():
    """Mock asyncssh connection for testing"""
    mock_conn = Mock()
    mock_conn.close = Mock()
    mock_conn.is_closed = Mock(return_value=False)
    mock_conn.run = Mock()
    return mock_conn


@pytest.fixture
def test_app(mock_env_vars):
    """FastAPI test application"""
    from app.scripts.api import app

    return app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Setup test database tables"""
    # Form database URL from environment variables
    from app.db.database_connection_manager import get_database_url

    database_url = get_database_url()
    # Database name is already set to kubeeye-db-test in environment

    async def create_tables():
        # Create async engine
        engine = create_async_engine(database_url, echo=False)
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    async def drop_tables():
        # Create async engine
        engine = create_async_engine(database_url, echo=False)
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    # Run async setup
    asyncio.run(create_tables())

    yield

    # Cleanup: drop all tables
    asyncio.run(drop_tables())


@pytest.fixture
async def db_session():
    """Database session for individual tests"""
    from app.db.database_connection_manager import get_database_url

    database_url = get_database_url()
    # Database name is already set to kubeeye-db-test in environment
    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        await engine.dispose()


@pytest.fixture(autouse=True)
def clear_clusters_cache():
    """Clear clusters cache before each test"""
    from services.cluster_service import ClusterService

    # Create a service instance to clear its cache
    service = ClusterService()
    service._clusters_cache.clear()


@pytest.fixture
def mock_task_manager():
    """Mock task manager for testing"""
    mock_manager = Mock()
    mock_manager.get_all_tasks = AsyncMock(return_value=[])
    mock_manager.get_task = AsyncMock(return_value=None)
    mock_manager.create_task = AsyncMock(return_value=None)
    mock_manager.delete_task = AsyncMock(return_value=False)
    mock_manager.update_task = AsyncMock(return_value=False)
    mock_manager.run_task_now = AsyncMock(return_value={"success": False, "message": "Task failed"})
    return mock_manager


@pytest.fixture
def mock_report_cleanup_service():
    """Mock report cleanup service for testing"""
    mock_service = Mock()
    mock_service.cleanup_old_reports = AsyncMock(
        return_value={"deleted_count": 10, "retention_days": 7, "message": "Successfully deleted 10 old reports"}
    )
    mock_service.get_cleanup_stats = AsyncMock(
        return_value={
            "total_records": 100,
            "old_records": 20,
            "recent_records": 80,
            "retention_days": 7,
            "cleanup_percentage": 20.0,
        }
    )
    mock_service.cleanup_reports_by_cluster = AsyncMock(
        return_value={
            "deleted_count": 5,
            "cluster_name": "test-cluster",
            "retention_days": 7,
            "message": "Successfully deleted 5 old reports for cluster 'test-cluster'",
        }
    )
    return mock_service


@pytest.fixture
def mock_gitops_manager():
    """Mock GitOps manager for testing"""
    mock_manager = Mock()
    mock_manager.load_config = Mock(return_value={"repository": {"url": "https://github.com/test/repo.git"}})
    mock_manager.clone_or_update_repo = Mock(return_value=(True, "Repository synchronized"))
    return mock_manager


@pytest.fixture
def mock_load_result():
    """Mock load_inspection_result function for reports testing"""
    with patch("api.reports.load_inspection_result") as mock_load:
        mock_load.return_value = {
            "result_id": "test-result",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00Z",
            "data": {"summary": "test data"},
        }
        yield mock_load


@pytest.fixture
def mock_database_connection_manager():
    """Mock DatabaseConnectionManager for testing"""
    mock_manager = Mock()
    mock_manager.get_db = AsyncMock()
    mock_manager.init_database = AsyncMock()
    mock_manager.drop_database = AsyncMock()
    mock_manager.get_engine = Mock()
    mock_manager.get_session_local = Mock()
    mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_manager.close_database = AsyncMock()
    return mock_manager


@pytest.fixture
def mock_database_monitor():
    """Mock DatabaseMonitor for testing"""
    mock_monitor = Mock()
    mock_monitor.start_monitoring = AsyncMock()
    mock_monitor.stop_monitoring = AsyncMock()
    mock_monitor.force_recovery = AsyncMock(return_value=True)
    mock_monitor.get_status = Mock(
        return_value={
            "running": True,
            "check_interval": 30,
            "failure_threshold": 3,
            "failure_count": 0,
            "stats": {"total_checks": 10, "successful_checks": 10},
        }
    )
    return mock_monitor
