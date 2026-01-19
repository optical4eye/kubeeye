import React, { useState, useEffect } from 'react';
import { Card, Select, Button, message, Space, Tag, List, Typography, Spin, Radio } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import { getClusters } from '../services/api';
import { getTaskStatusIcon } from '../components/statusUtils';
import { useTaskWebSocket } from '../hooks/useTaskWebSocket';

const { Option } = Select;

interface Task {
  task_id: string;
  task_type: string;
  status: string;
  created_at: string;
  payload?: any;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
}

interface Cluster {
  name: string;
  nodes?: any[];
}

const PopeyeScan = () => {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  // Popeye reports are only available in HTML format
  const outputFormat = 'html';
  const [allNamespaces, setAllNamespaces] = useState(true);
  const [selectedNamespace, setSelectedNamespace] = useState(null);
  const [availableNamespaces, setAvailableNamespaces] = useState([]);
  const [loadingNamespaces, setLoadingNamespaces] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const { startTaskMonitoring, handleCancelTask } = useTaskWebSocket(activeTasks, setActiveTasks);

  const loadClusters = async () => {
    try {
      const response = await getClusters();
      setClusters(response.data.clusters || []);
    } catch (error) {
      message.error('Ошибка загрузки кластеров');
      console.error(error);
    }
  };

  const loadNamespaces = async clusterName => {
    try {
      setLoadingNamespaces(true);
      const { getPopeyeNamespaces } = await import('../services/api');
      const response = await getPopeyeNamespaces(clusterName);
      setAvailableNamespaces(response.data.namespaces || []);
    } catch (error) {
      message.error('Ошибка загрузки namespace');
      console.error(error);
      setAvailableNamespaces([]);
    } finally {
      setLoadingNamespaces(false);
    }
  };

  useEffect(() => {
    loadClusters();
  }, []);

  // Load namespaces when cluster is selected
  useEffect(() => {
    if (selectedCluster) {
      loadNamespaces(selectedCluster);
    } else {
      setAvailableNamespaces([]);
      setSelectedNamespace(null);
    }
  }, [selectedCluster]);

  const handleRunPopeyeScan = async () => {
    if (!selectedCluster) {
      message.error('Выберите кластер');
      return;
    }

    const scanData = {
      cluster_name: selectedCluster,
      output_format: outputFormat,
      all_namespaces: allNamespaces,
      namespace: allNamespaces ? null : selectedNamespace,
    };

    try {
      setLoading(true);

      // Import here to avoid circular dependency
      const { startPopeyeScan } = await import('../services/api');
      const response = await startPopeyeScan(scanData);
      const taskId = response.data.task_id;

      const newTask = {
        task_id: taskId,
        task_type: 'popeye',
        status: 'pending',
        created_at: new Date().toISOString(),
        payload: scanData,
      };

      setActiveTasks(prev => [newTask, ...prev]);
      startTaskMonitoring(taskId);

      message.success(`Popeye сканирование запущено (ID: ${taskId})`);
    } catch (error) {
      if (error.response?.data?.detail) {
        message.error(`Ошибка: ${error.response.data.detail}`);
      } else {
        message.error('Ошибка запуска Popeye сканирования');
      }
      console.error('Popeye scan error:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTaskTime = isoString => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString();
  };

  return (
    <div>
      <div className="page-title">Popeye - Сканирование кластеров</div>
      <div className="page-subtitle">
        Автоматическое сканирование Kubernetes кластеров на предмет потенциальных проблем и лучших
        практик
      </div>

      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <div aria-label="Выберите кластер для сканирования">
              Выберите кластер для сканирования:
            </div>
            <Select
              className="margin-top-space-2"
              style={{ width: '100%' }}
              placeholder="Выберите кластер"
              onChange={setSelectedCluster}
              value={selectedCluster}
            >
              {clusters.map(cluster => (
                <Option key={cluster.name} value={cluster.name}>
                  {cluster.name} ({cluster.nodes?.length || 0} узлов)
                </Option>
              ))}
            </Select>
          </div>

          <div className="margin-top-space-4">
            <div className="text-muted">Popeye отчеты доступны только в HTML формате</div>
          </div>

          <div className="margin-top-space-4">
            <div aria-label="Выберите область сканирования">Выберите область сканирования:</div>
            <Radio.Group
              value={allNamespaces ? 'all' : 'specific'}
              onChange={e => setAllNamespaces(e.target.value === 'all')}
              className="margin-top-space-2"
            >
              <Radio value="all">Все namespaces</Radio>
              <Radio value="specific">Конкретный namespace</Radio>
            </Radio.Group>
            {!allNamespaces && (
              <Select
                className="margin-top-space-2"
                style={{ width: '100%' }}
                placeholder={loadingNamespaces ? 'Загрузка namespace...' : 'Выберите namespace'}
                onChange={setSelectedNamespace}
                value={selectedNamespace}
                loading={loadingNamespaces}
                disabled={!selectedCluster || loadingNamespaces}
              >
                {availableNamespaces.map(ns => (
                  <Option key={ns} value={ns}>
                    {ns}
                  </Option>
                ))}
              </Select>
            )}
          </div>

          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleRunPopeyeScan}
            loading={loading}
            disabled={!selectedCluster}
            size="large"
            className="margin-top-space-4"
          >
            Запустить сканирование Popeye
          </Button>
        </Space>
      </Card>

      {/* Active Tasks Section */}
      {activeTasks.length > 0 && (
        <Card title="Активные задачи сканирования" className="margin-top-space-4">
          <List
            dataSource={activeTasks}
            renderItem={task => (
              <List.Item
                actions={[
                  (task.status === 'running' || task.status === 'pending') && (
                    <Button
                      danger
                      size="small"
                      onClick={() => handleCancelTask(task.task_id)}
                      icon={<StopOutlined />}
                    >
                      Отменить
                    </Button>
                  ),
                ]}
              >
                <List.Item.Meta
                  avatar={getTaskStatusIcon(task.status)}
                  title={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <Typography.Text strong>
                          Задача {task.task_id.split('_')[1]}
                        </Typography.Text>
                        <Tag className={`status-${task.status}`}>
                          {task.status === 'pending' && 'Ожидает'}
                          {task.status === 'running' && 'Выполняется'}
                          {task.status === 'completed' && 'Завершена'}
                          {task.status === 'failed' && 'Ошибка'}
                          {task.status === 'cancelled' && 'Отменена'}
                        </Tag>
                      </Space>
                      {task.status === 'running' && <Spin size="small" />}
                    </Space>
                  }
                  description={
                    <div>
                      <div>Кластер: {task.payload?.cluster_name}</div>
                      <div>Формат: {task.payload?.output_format?.toUpperCase()}</div>
                      <div>
                        Namespaces:{' '}
                        {task.payload?.all_namespaces
                          ? 'Все'
                          : task.payload?.namespace || 'Указанный'}
                      </div>
                      <div>Создано: {formatTaskTime(task.created_at)}</div>
                      {task.started_at && <div>Запущено: {formatTaskTime(task.started_at)}</div>}
                      {(task.completed_at || task.status === 'failed') && (
                        <div>Завершено: {formatTaskTime(task.completed_at)}</div>
                      )}
                      {task.error && (
                        <div style={{ color: 'var(--error-color)', marginTop: 4 }}>
                          Ошибка: {task.error}
                        </div>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
};

export default PopeyeScan;
