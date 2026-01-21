import React, { useState, useEffect } from 'react';
import { Card, Select, Button, message, Space, Tag, List, Typography, Spin, Radio } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getClusters } from '../services/api';
import { getTaskStatusIcon } from '../components/ui/statusUtils';
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
  const { t } = useTranslation();
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
      message.error(t('popeye.errors.loadClusters'));
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
     message.error(t('popeye.errors.loadNamespaces'));
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
       message.error(t('popeye.errors.selectCluster'));
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

      message.success(t('popeye.errors.scanStarted', { taskId }));
    } catch (error) {
      if (error.response?.data?.detail) {
        message.error(t('popeye.errors.error', { detail: error.response.data.detail }));
      } else {
        message.error(t('popeye.errors.startError'));
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
      <div className="page-title">{t('popeye.title')}</div>
      <div className="page-subtitle">
        {t('popeye.subtitle')}
      </div>

      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <div aria-label={t('popeye.selectCluster')}>
              {t('popeye.selectCluster')}
            </div>
            <Select
              className="margin-top-space-2"
              style={{ width: '100%' }}
              placeholder={t('popeye.selectClusterPlaceholder')}
              onChange={setSelectedCluster}
              value={selectedCluster}
            >
              {clusters.map(cluster => (
                <Option key={cluster.name} value={cluster.name}>
                  {cluster.name} ({cluster.nodes?.length || 0} {t('popeye.nodes')})
                </Option>
              ))}
            </Select>
          </div>

          <div className="margin-top-space-4">
            <div className="text-muted">{t('popeye.htmlOnly')}</div>
          </div>

          <div className="margin-top-space-4">
            <div aria-label={t('popeye.scanArea')}>{t('popeye.scanArea')}</div>
            <Radio.Group
              value={allNamespaces ? 'all' : 'specific'}
              onChange={e => setAllNamespaces(e.target.value === 'all')}
              className="margin-top-space-2"
            >
              <Radio value="all">{t('popeye.allNamespaces')}</Radio>
              <Radio value="specific">{t('popeye.specificNamespace')}</Radio>
            </Radio.Group>
            {!allNamespaces && (
              <Select
                className="margin-top-space-2"
                style={{ width: '100%' }}
                placeholder={loadingNamespaces ? t('popeye.loadingNamespaces') : t('popeye.selectNamespace')}
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
            {t('popeye.startScan')}
          </Button>
        </Space>
      </Card>

      {/* Active Tasks Section */}
      {activeTasks.length > 0 && (
        <Card title={t('popeye.activeTasks')} className="margin-top-space-4">
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
                      {t('popeye.cancel')}
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
                          {t('popeye.task')} {task.task_id.split('_')[1]}
                        </Typography.Text>
                        <Tag className={`status-${task.status}`}>
                          {t(`popeye.status.${task.status}`)}
                        </Tag>
                      </Space>
                      {task.status === 'running' && <Spin size="small" />}
                    </Space>
                  }
                  description={
                    <div>
                      <div>{t('popeye.details.cluster')} {task.payload?.cluster_name}</div>
                      <div>{t('popeye.details.format')} {task.payload?.output_format?.toUpperCase()}</div>
                      <div>
                        {t('popeye.details.namespaces')}{' '}
                        {task.payload?.all_namespaces
                          ? t('popeye.details.all')
                          : task.payload?.namespace || t('popeye.details.specified')}
                      </div>
                      <div>{t('popeye.details.created')} {formatTaskTime(task.created_at)}</div>
                      {task.started_at && <div>{t('popeye.details.started')} {formatTaskTime(task.started_at)}</div>}
                      {(task.completed_at || task.status === 'failed') && (
                        <div>{t('popeye.details.completed')} {formatTaskTime(task.completed_at)}</div>
                      )}
                      {task.error && (
                        <div style={{ color: 'var(--error-color)', marginTop: 4 }}>
                          {t('popeye.details.error')} {task.error}
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
