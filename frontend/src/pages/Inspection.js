import React, { useState, useEffect, useRef } from 'react';
import { Card, Tabs, Select, Button, message, Space, Checkbox, Tag, List, Typography } from 'antd';
import { PlayCircleOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, StopOutlined } from '@ant-design/icons';
import { getClusters, runInspectionAsync, getInspectionTaskStatus, cancelInspectionTask, getRules } from '../services/api';
import ScheduledInspection from '../components/ScheduledInspection';
import RuleManagement from '../components/RuleManagement';

const { TabPane } = Tabs;
const { Option } = Select;

const Inspection = () => {
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [rules, setRules] = useState({});
  const [selectedRules, setSelectedRules] = useState({ node: [], prometheus: [], opa: [] });
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

  const loadRules = async () => {
    try {
      const response = await getRules();
      setRules(response.data.rules || {});
    } catch (error) {
      message.error('Ошибка загрузки правил');
      console.error(error);
    }
  };

  useEffect(() => {
    loadClusters();
    loadRules();
  }, []);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals.current).forEach(interval => {
        clearInterval(interval);
      });
      pollingIntervals.current = {};
    };
  }, []);

  useEffect(() => {
    const newSelectedRules = {};
    Object.keys(rules).forEach(ruleType => {
      newSelectedRules[ruleType] = rules[ruleType]?.map(rule => rule.id) || [];
    });
    setSelectedRules(newSelectedRules);
  }, [rules]);

  const startTaskPolling = (taskId) => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
    }

    const interval = setInterval(async () => {
      try {
        const response = await getInspectionTaskStatus(taskId);
        const task = response.data;

        setActiveTasks(prev => prev.map(t => t.task_id === taskId ? task : t));

        // Stop polling when task is completed or failed
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollingIntervals.current[taskId]);
          delete pollingIntervals.current[taskId];

          if (task.status === 'completed') {
            message.success(`Задача ${taskId} завершена успешно`);
          } else {
            message.error(`Задача ${taskId} завершилась с ошибкой: ${task.error}`);
          }
        }
      } catch (error) {
        console.error(`Error polling task ${taskId}:`, error);
        clearInterval(pollingIntervals.current[taskId]);
        delete pollingIntervals.current[taskId];
      }
    }, 2000); // Poll every 2 seconds

    pollingIntervals.current[taskId] = interval;
  };

  const stopTaskPolling = (taskId) => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
      delete pollingIntervals.current[taskId];
    }
  };

  const handleCancelTask = async (taskId) => {
    try {
      await cancelInspectionTask(taskId);
      stopTaskPolling(taskId);
      setActiveTasks(prev => prev.map(t =>
        t.task_id === taskId ? { ...t, status: 'cancelled' } : t
      ));
      message.success('Задача отменена');
    } catch (error) {
      message.error('Ошибка отмены задачи');
      console.error(error);
    }
  };

  const handleRunInspection = async () => {
    if (!selectedCluster) {
      message.error('Выберите кластер');
      return;
    }

    const totalSelectedRules = Object.values(selectedRules).reduce((sum, arr) => sum + arr.length, 0);
    if (totalSelectedRules === 0) {
      message.error('Выберите хотя бы одно правило');
      return;
    }

    const inspectionData = {
      cluster_name: selectedCluster,
      selected_rules: selectedRules,
      inspection_type: 'immediate'
    };

    try {
      setLoading(true);

      // Async mode only
      const response = await runInspectionAsync(inspectionData);
      const taskId = response.data.task_id;

      const newTask = {
        task_id: taskId,
        task_type: 'inspection',
        status: 'pending',
        created_at: new Date().toISOString(),
        payload: inspectionData
      };

      setActiveTasks(prev => [newTask, ...prev]);
      startTaskPolling(taskId);

      message.success(`Инспекция запущена (ID: ${taskId})`);

    } catch (error) {
      // Handle different types of errors
      if (error.code === 'ECONNABORTED') {
        message.error(`Таймаут подключения к кластеру ${selectedCluster}. Проверьте доступность узлов кластера.`);
      } else if (error.message && error.message.includes('timeout')) {
        message.error(`Не удалось выполнить инспекцию кластера ${selectedCluster} из-за таймаута подключения`);
      } else if (error.response?.status === 500) {
        message.error('Ошибка сервера при выполнении инспекции');
      } else if (error.response?.data?.detail) {
        message.error(`Ошибка: ${error.response.data.detail}`);
      } else {
        message.error('Ошибка выполнения инспекции');
      }
      console.error('Inspection error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRuleSelection = (ruleType, ruleIds) => {
    setSelectedRules(prev => ({
      ...prev,
      [ruleType]: ruleIds
    }));
  };

  const getTaskStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'cancelled':
        return <StopOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  const getTaskStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'orange';
      case 'running':
        return 'blue';
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  const formatTaskTime = (isoString) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString();
  };

  const renderRuleSelection = (ruleType, title) => {
    const availableRules = rules[ruleType] || [];
    const selected = selectedRules[ruleType] || [];
    const allSelected = availableRules.length > 0 && selected.length === availableRules.length;
    const someSelected = selected.length > 0 && selected.length < availableRules.length;

    const handleSelectAll = (checked) => {
      if (checked) {
        handleRuleSelection(ruleType, availableRules.map(rule => rule.id));
      } else {
        handleRuleSelection(ruleType, []);
      }
    };

    return (
      <Card title={title} size="small">
        {availableRules.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <Checkbox
              indeterminate={someSelected}
              checked={allSelected}
              onChange={(e) => handleSelectAll(e.target.checked)}
            >
              Выбрать все ({availableRules.length})
            </Checkbox>
          </div>
        )}
        <Checkbox.Group
          value={selected}
          onChange={(values) => handleRuleSelection(ruleType, values)}
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {availableRules.map(rule => (
              <Checkbox key={rule.id} value={rule.id}>
                <div>
                  <strong>{rule.name}</strong>
                  <div style={{ fontSize: '12px', color: '#f8f8f2' }}>
                    {rule.description}
                  </div>
                </div>
              </Checkbox>
            ))}
          </Space>
        </Checkbox.Group>
      </Card>
    );
  };

  return (
    <div>
      <div className="page-title">Центр инспекции кластеров</div>
      <div className="page-subtitle">Выполнение немедленной или запланированной инспекции, управление правилами инспекции</div>

      <Tabs defaultActiveKey="1">
        <TabPane tab="Немедленная инспекция" key="1">
          <Card>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <label>Выберите кластер для инспекции:</label>
                <Select
                  style={{ width: '100%', marginTop: 8 }}
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



              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                {renderRuleSelection('node', 'Правила узлов')}
                {renderRuleSelection('opa', 'Правила Kubernetes')}
                {renderRuleSelection('prometheus', 'Правила мониторинга')}
              </div>

              {/* Summary of selected rules */}
              {Object.values(selectedRules).some(arr => arr.length > 0) && (
                <Card size="small" style={{ marginTop: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>Выбранные правила:</strong>
                      <div style={{ marginTop: 8 }}>
                        {Object.entries(selectedRules).map(([type, rules]) => (
                          rules.length > 0 && (
                            <div key={type} style={{ marginBottom: 4 }}>
                              <span style={{ fontWeight: 'bold' }}>
                                {type === 'node' ? 'Узлы' : type === 'prometheus' ? 'Мониторинг' : 'Kubernetes'}:
                              </span> {rules.length} правил
                            </div>
                          )
                        ))}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#bd93f9' }}>
                        {Object.values(selectedRules).reduce((sum, arr) => sum + arr.length, 0)}
                      </div>
                      <div style={{ fontSize: '12px', color: '#6272a4' }}>всего правил</div>
                    </div>
                  </div>
                </Card>
              )}


              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleRunInspection}
                loading={loading}
                disabled={!selectedCluster || Object.values(selectedRules).every(arr => arr.length === 0)}
                size="large"
                style={{ marginTop: 16 }}
              >
                Запустить инспекцию
              </Button>
            </Space>
          </Card>

          {/* Active Tasks Section */}
          {activeTasks.length > 0 && (
            <Card title="Активные задачи" style={{ marginTop: 16 }}>
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
                      )
                    ]}
                  >
                    <List.Item.Meta
                      avatar={getTaskStatusIcon(task.status)}
                      title={
                        <Space>
                          <Typography.Text strong>
                            Задача {task.task_id.split('_')[1]}
                          </Typography.Text>
                          <Tag color={getTaskStatusColor(task.status)}>
                            {task.status === 'pending' && 'Ожидает'}
                            {task.status === 'running' && 'Выполняется'}
                            {task.status === 'completed' && 'Завершена'}
                            {task.status === 'failed' && 'Ошибка'}
                            {task.status === 'cancelled' && 'Отменена'}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div>
                          <div>Кластер: {task.payload?.cluster_name}</div>
                          <div>Создано: {formatTaskTime(task.created_at)}</div>
                          {task.started_at && (
                            <div>Запущено: {formatTaskTime(task.started_at)}</div>
                          )}
                          {(task.completed_at || task.status === 'failed') && (
                            <div>Завершено: {formatTaskTime(task.completed_at)}</div>
                          )}
                          {task.error && (
                            <div style={{ color: '#ff4d4f', marginTop: 4 }}>
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
        </TabPane>

        <TabPane tab="Запланированная инспекция" key="2">
          <ScheduledInspection />
        </TabPane>

        <TabPane tab="Управление правилами" key="3">
          <RuleManagement />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Inspection;