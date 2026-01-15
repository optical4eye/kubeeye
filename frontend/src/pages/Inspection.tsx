import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Tabs,
  Select,
  Button,
  message,
  Space,
  Tag,
  List,
  Typography,
  Progress,
  theme,
} from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import {
  getClusters,
  runInspectionAsync,
  getInspectionTaskStatus,
  cancelInspectionTask,
  getRules,
  getRuleTags,
} from '../services/api';
import ScheduledInspection from '../components/ScheduledInspection';
import RuleManagement from '../components/RuleManagement';
import RuleSelector from '../components/RuleSelector';
import { getTaskStatusIcon } from '../components/statusUtils';

const { TabPane } = Tabs;
const { Option } = Select;

const Inspection = () => {
  const { token } = theme.useToken();
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [rules, setRules] = useState({});
  const [selectedRules, setSelectedRules] = useState({ node: [], opa: [] });
  const [availableTags, setAvailableTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
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

  const loadRules = async (tags = null) => {
    try {
      const response = await getRules(tags);
      setRules(response.data.rules || {});
    } catch (error) {
      message.error('Ошибка загрузки правил');
      console.error(error);
    }
  };

  const loadTags = async () => {
    try {
      const response = await getRuleTags();
      setAvailableTags(response.data.tags || []);
    } catch (error) {
      message.error('Ошибка загрузки тегов');
      console.error(error);
    }
  };

  const getAllTags = () => {
    return availableTags;
  };

  useEffect(() => {
    loadClusters();
    loadTags();
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

  useEffect(() => {
    loadRules(selectedTags.length > 0 ? selectedTags : null);
  }, [selectedTags]);

  const startTaskPolling = taskId => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
    }

    const interval = setInterval(async () => {
      try {
        const response = await getInspectionTaskStatus(taskId);
        const task = response.data;

        setActiveTasks(prev => prev.map(t => (t.task_id === taskId ? task : t)));

        // Stop polling when task is completed or failed
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollingIntervals.current[taskId]);
          delete pollingIntervals.current[taskId];

          if (task.status === 'completed') {
            message.success(
              `Задача ${taskId} завершена успешно. Отчет доступен в разделе "Отчеты"`
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
            message.error(`Задача ${taskId} завершилась с ошибкой: ${task.error}`);
          }
        }
      } catch (error) {
        console.error(`Error polling task ${taskId}:`, error);

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
      await cancelInspectionTask(taskId);
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

  const handleRunInspection = async () => {
    if (!selectedCluster) {
      message.error('Выберите кластер');
      return;
    }

    const totalSelectedRules = Object.values(selectedRules).reduce(
      (sum, arr) => sum + arr.length,
      0
    );
    if (totalSelectedRules === 0) {
      message.error('Выберите хотя бы одно правило');
      return;
    }

    const inspectionData = {
      cluster_name: selectedCluster,
      selected_rules: selectedRules,
      inspection_type: 'immediate',
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
        payload: inspectionData,
      };

      setActiveTasks(prev => [newTask, ...prev]);
      startTaskPolling(taskId);

      message.success(`Инспекция запущена (ID: ${taskId})`);
    } catch (error) {
      // Handle different types of errors
      if (error.code === 'ECONNABORTED') {
        message.error(
          `Таймаут подключения к кластеру ${selectedCluster}. Проверьте доступность узлов кластера.`
        );
      } else if (error.message && error.message.includes('timeout')) {
        message.error(
          `Не удалось выполнить инспекцию кластера ${selectedCluster} из-за таймаута подключения`
        );
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
      [ruleType]: ruleIds,
    }));
  };

  const formatTaskTime = isoString => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString();
  };

  return (
    <div>
      <div className="page-title">Центр инспекции кластеров</div>
      <div className="page-subtitle">
        Выполнение немедленной или запланированной инспекции, управление правилами инспекции
      </div>

      <Tabs defaultActiveKey="1">
        <TabPane tab="Немедленная инспекция" key="1">
          <Card>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <div aria-label="Выберите кластер для инспекции">
                  Выберите кластер для инспекции:
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

              {/* Tag Filter */}
              {getAllTags().length > 0 && (
                <div>
                  <div aria-label="Фильтр по тегам правил">
                    Фильтр по тегам правил (опционально):
                  </div>
                  <Select
                    mode="multiple"
                    className="margin-top-space-2"
                    style={{ width: '100%' }}
                    placeholder="Выберите теги для фильтрации правил"
                    onChange={setSelectedTags}
                    value={selectedTags}
                    allowClear
                    options={getAllTags().map(({ tag, count }) => ({
                      value: tag,
                      label: `${tag} (${count})`,
                    }))}
                  />
                </div>
              )}

              <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
                <div style={{ flex: 1 }}>
                  <RuleSelector
                    ruleType="node"
                    title="Правила узлов"
                    availableRules={rules.node || []}
                    selectedRules={selectedRules}
                    onRuleSelection={handleRuleSelection}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <RuleSelector
                    ruleType="opa"
                    title="Правила Kubernetes"
                    availableRules={rules.opa || []}
                    selectedRules={selectedRules}
                    onRuleSelection={handleRuleSelection}
                  />
                </div>
              </div>

              {/* Summary of selected rules */}
              {Object.values(selectedRules).some(arr => arr.length > 0) && (
                <Card size="small" className="margin-top-space-4">
                  <div className="flex-space-between">
                    <div>
                      <strong>Выбранные правила:</strong>
                      <div className="margin-top-space-2">
                        {Object.entries(selectedRules).map(
                          ([type, rules]) =>
                            rules.length > 0 && (
                              <div key={type} style={{ marginBottom: token.marginXXS }}>
                                <span style={{ fontWeight: 'bold' }}>
                                  {type === 'node' ? 'Узлы' : 'Kubernetes'}:
                                </span>{' '}
                                {rules.length} правил
                              </div>
                            )
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-bold text-accent">
                        {Object.values(selectedRules).reduce((sum, arr) => sum + arr.length, 0)}
                      </div>
                      <div className="text-xs text-secondary">всего правил</div>
                    </div>
                  </div>
                </Card>
              )}

              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleRunInspection}
                loading={loading}
                disabled={
                  !selectedCluster || Object.values(selectedRules).every(arr => arr.length === 0)
                }
                size="large"
                className="margin-top-space-4"
              >
                Запустить инспекцию
              </Button>
            </Space>
          </Card>

          {/* Active Tasks Section */}
          {activeTasks.length > 0 && (
            <Card title="Активные задачи" className="margin-top-space-4">
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
                          {task.status === 'running' && (
                            <Progress
                              percent={100}
                              status="active"
                              showInfo={false}
                              size="small"
                              strokeColor={{
                                '0%': 'var(--ant-color-primary)',
                                '100%': 'var(--ant-color-success)',
                              }}
                            />
                          )}
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
                            <div
                              style={{ color: 'var(--error-color)', marginTop: token.marginXXS }}
                            >
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
