import React, { useState, useEffect, useRef } from 'react';
import { Card, Select, Button, message, Space, Tag, List, Typography, Spin, Radio } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import { getClusters } from '../services/api';
import { getTaskStatusIcon } from '../components/statusUtils';

const { Option } = Select;

const PopeyeScan = () => {
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  // Popeye reports are only available in HTML format
  const outputFormat = 'html';
  const [allNamespaces, setAllNamespaces] = useState(true);
  const [selectedNamespace, setSelectedNamespace] = useState(null);
  const [availableNamespaces, setAvailableNamespaces] = useState([]);
  const [loadingNamespaces, setLoadingNamespaces] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTasks, setActiveTasks] = useState([]);
  const pollingIntervals = useRef({});

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

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals.current).forEach(interval => {
        clearInterval(interval);
      });
      pollingIntervals.current = {};
    };
  }, []);

  const startTaskPolling = taskId => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
    }

    const interval = setInterval(async () => {
      try {
        // Import here to avoid circular dependency
        const { getPopeyeTaskStatus } = await import('../services/api');
        const response = await getPopeyeTaskStatus(taskId);
        const task = response.data;

        setActiveTasks(prev => prev.map(t => (t.task_id === taskId ? task : t)));

        // Stop polling when task is completed or failed
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollingIntervals.current[taskId]);
          delete pollingIntervals.current[taskId];

          if (task.status === 'completed') {
            message.success(
              `Popeye сканирование ${taskId} завершено успешно. Отчет доступен в разделе "Отчеты"`
            );

            // Trigger a custom event to notify other components about the new report
            window.dispatchEvent(
              new CustomEvent('newReportAvailable', {
                detail: {
                  taskId,
                  result: task.result,
                },
              })
            );
          } else {
            message.error(`Popeye сканирование ${taskId} завершилось с ошибкой: ${task.error}`);
          }
        }
      } catch (error) {
        console.error(`Error polling Popeye task ${taskId}:`, error);

        // Check if it's a 404 error (task not found)
        if (error.response?.status === 404) {
          message.error(
            `Задача ${taskId} не найдена. Возможно, она была удалена или истек срок действия.`
          );
        } else {
          message.error(`Ошибка при проверке статуса задачи ${taskId}: ${error.message}`);
        }

        clearInterval(pollingIntervals.current[taskId]);
        delete pollingIntervals.current[taskId];

        // Update task status to show error in UI
        setActiveTasks(prev =>
          prev.map(t =>
            t.task_id === taskId ? { ...t, status: 'failed', error: error.message } : t
          )
        );
      }
    }, 2000); // Poll every 2 seconds

    pollingIntervals.current[taskId] = interval;
  };

  const stopTaskPolling = taskId => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
      delete pollingIntervals.current[taskId];
    }
  };

  const handleCancelTask = async taskId => {
    try {
      // Import here to avoid circular dependency
      const { cancelPopeyeTask } = await import('../services/api');
      await cancelPopeyeTask(taskId);
      stopTaskPolling(taskId);
      setActiveTasks(prev =>
        prev.map(t => (t.task_id === taskId ? { ...t, status: 'cancelled' } : t))
      );
      message.success('Задача отменена');
    } catch (error) {
      message.error('Ошибка отмены задачи');
      console.error(error);
    }
  };

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
      startTaskPolling(taskId);

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
