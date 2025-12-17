# pytest fixtures for KubeEye backend tests

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch


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
        "KUBEYE_REPORT_RETENTION_DAYS": "7",
        "KUBEYE_SSH_CONNECTION_TIMEOUT": "10",
        "KUBEYE_SSH_MAX_CONCURRENT_CHECKS": "5",
        "PYTHONPATH": "/app",
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
def test_app(mock_env_vars):
    """FastAPI test application"""
    from scripts.api import app

    return app


@pytest.fixture(autouse=True)
def clear_clusters_cache():
    """Clear clusters cache before each test"""
    from api.clusters import _clusters_cache

    _clusters_cache.clear()
