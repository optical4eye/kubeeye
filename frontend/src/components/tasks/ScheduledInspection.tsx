import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  Modal,
  Form,
  Select,
  DatePicker,
  TimePicker,
  Input,
  Switch,
  Space,
  message,
  Tabs,
  Alert,
} from 'antd';
import { DeleteOutlined, PlayCircleFilled, EditOutlined } from '@ant-design/icons';
import { format, parseISO, parse } from 'date-fns';
import { useTranslation } from 'react-i18next';
import * as api from '../../services/api';
import { RuleSelector } from '../rules';
import { getStatusTag } from '../ui/statusUtils';
import { Task, Cluster, Rule } from '../../types';

const { Option } = Select;

const ScheduledInspection = () => {
  const { t } = useTranslation();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [rules, setRules] = useState<Record<string, Rule[]>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [editModalVisible, setEditModalVisible] = useState<boolean>(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [selectedRules, setSelectedRules] = useState<Record<string, number[]>>({
    node: [],
    opa: [],
  });
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const handleRuleSelection = (ruleType: string, ruleIds: number[]) => {
    setSelectedRules(prev => ({
      ...prev,
      [ruleType]: ruleIds,
    }));
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [tasksRes, clustersRes, rulesRes] = await Promise.all([
        api.getScheduledTasks(),
        api.getClusters(),
        api.getRules(),
      ]);
      setTasks(tasksRes.data.tasks || []);
      setClusters(clustersRes.data.clusters || []);
      setRules(rulesRes.data.rules || {});
    } catch (error) {
      message.error(t('scheduledInspection.errorLoadingData'));
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateTask = async (values: any) => {
    try {
      let cronExpr = '';
      let runDatetime = null;

      if (values.schedule_type === 'cron') {
        // Собираем cron выражение
        cronExpr = `${values.cron_min || '0'} ${values.cron_hour || '8'} ${values.cron_dom || '*'} ${values.cron_month || '*'} ${values.cron_dow || '*'}`;
      } else {
        // Одноразовая задача
        const dateTime = `${format(values.run_date.toDate(), 'yyyy-MM-dd')} ${format(values.run_time.toDate(), 'HH:mm')}`;
        runDatetime = dateTime;
      }

      const taskData = {
        name: values.name,
        description: values.description,
        cluster: values.cluster,
        cron_expr: cronExpr,
        rules: {
          node: selectedRules.node,
          opa: selectedRules.opa,
        },
        enabled: values.enabled,
        task_type: values.schedule_type === 'cron' ? 'cron' : 'once',
        run_datetime: runDatetime,
      };

      await api.createScheduledTask(taskData);
      message.success(t('scheduledInspection.taskCreated'));
      form.resetFields();
      setSelectedRules({ node: [], opa: [] });
      loadData();
    } catch (error) {
      message.error(t('scheduledInspection.errorCreatingTask'));
      console.error(error);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await api.deleteScheduledTask(taskId);
      message.success(t('scheduledInspection.taskDeleted'));
      loadData();
    } catch (error) {
      message.error(t('scheduledInspection.errorDeletingTask'));
      console.error(error);
    }
  };

  const handleRunTask = async (taskId: string) => {
    try {
      await api.runScheduledTask(taskId);
      message.success(t('scheduledInspection.taskRun'));
      loadData();
    } catch (error) {
      message.error(t('scheduledInspection.errorRunningTask'));
      console.error(error);
    }
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setSelectedRules({
      node: task.rules?.node || [],
      opa: task.rules?.opa || [],
    });

    editForm.setFieldsValue({
      name: task.name,
      description: task.description,
      cluster: task.cluster,
      schedule_type: task.task_type === 'once' ? 'once' : 'cron',
      enabled: task.enabled,
    });

    if (task.task_type === 'once' && task.run_datetime) {
      const [date, time] = task.run_datetime.split(' ');
      editForm.setFieldsValue({
        run_date: parseISO(date),
        run_time: parse(time, 'HH:mm', new Date()),
      });
    } else if (task.cron_expr) {
      const cronParts = task.cron_expr.split(' ');
      if (cronParts.length >= 5) {
        editForm.setFieldsValue({
          cron_min: cronParts[0],
          cron_hour: cronParts[1],
          cron_dom: cronParts[2],
          cron_month: cronParts[3],
          cron_dow: cronParts[4],
        });
      }
    }

    setEditModalVisible(true);
  };

  const handleUpdateTask = async (values: any) => {
    try {
      let cronExpr = '';
      let runDatetime = null;

      if (values.schedule_type === 'cron') {
        cronExpr = `${values.cron_min || '0'} ${values.cron_hour || '8'} ${values.cron_dom || '*'} ${values.cron_month || '*'} ${values.cron_dow || '*'}`;
      } else {
        const dateTime = `${format(values.run_date.toDate(), 'yyyy-MM-dd')} ${format(values.run_time.toDate(), 'HH:mm')}`;
        runDatetime = dateTime;
      }

      const taskData = {
        name: values.name,
        description: values.description,
        cluster: values.cluster,
        cron_expr: cronExpr,
        rules: {
          node: selectedRules.node,
          opa: selectedRules.opa,
        },
        enabled: values.enabled,
        task_type: values.schedule_type === 'cron' ? 'cron' : 'once',
        run_datetime: runDatetime,
      };

      await api.updateScheduledTask(editingTask.task_id, taskData);
      message.success(t('scheduledInspection.taskUpdated'));
      setEditModalVisible(false);
      setEditingTask(null);
      editForm.resetFields();
      setSelectedRules({ node: [], opa: [] });
      loadData();
    } catch (error) {
      message.error(t('scheduledInspection.errorUpdatingTask'));
      console.error(error);
    }
  };

  const taskColumns = [
    { title: t('scheduledInspection.name'), dataIndex: 'name', key: 'name' },
    { title: t('scheduledInspection.cluster'), dataIndex: 'cluster', key: 'cluster' },
    {
      title: t('scheduledInspection.schedule'),
      dataIndex: 'cron_expr',
      key: 'cron_expr',
      render: (cron, record) => (record.task_type === 'once' ? t('scheduledInspection.oneTime') : cron),
    },
    { title: t('scheduledInspection.status'), dataIndex: 'last_status', key: 'last_status', render: getStatusTag },
    {
      title: t('scheduledInspection.enabled'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: enabled => <Switch checked={enabled} disabled />,
    },
    {
      title: t('scheduledInspection.lastRun'),
      dataIndex: 'last_run',
      key: 'last_run',
      render: date => (date ? new Date(date).toLocaleString() : t('scheduledInspection.neverRun')),
    },
    {
      title: t('scheduledInspection.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space wrap>
          <Button
            icon={<PlayCircleFilled />}
            onClick={() => handleRunTask(record.task_id)}
            title={t('scheduledInspection.runNow')}
          />
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditTask(record)}
            title={t('scheduledInspection.edit')}
          />
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={() =>
              Modal.confirm({
                title: t('scheduledInspection.deleteTask'),
                content: t('scheduledInspection.deleteConfirm'),
                onOk: () => handleDeleteTask(record.task_id),
              })
            }
          />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Tabs
        defaultActiveKey="1"
        items={[
          {
            key: '1',
            label: t('scheduledInspection.taskList'),
            children: (
              <Card>
                <Table
                  columns={taskColumns}
                  dataSource={tasks}
                  loading={loading}
                  rowKey="task_id"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: '2',
            label: t('scheduledInspection.createTask'),
            children: (
              <Card>
                <Form form={form} layout="vertical" onFinish={handleCreateTask}>
                  <Form.Item
                    name="name"
                    label={t('scheduledInspection.taskName')}
                    rules={[{ required: true, message: t('scheduledInspection.enterTaskName') }]}
                  >
                    <Input placeholder={t('scheduledInspection.dailyCheck')} />
                  </Form.Item>

                  <Form.Item
                    name="description"
                    label={t('scheduledInspection.description')}
                    rules={[{ required: true, message: t('scheduledInspection.enterDescription') }]}
                  >
                    <Input.TextArea placeholder={t('scheduledInspection.taskDescription')} />
                  </Form.Item>

                  <Form.Item
                    name="cluster"
                    label={t('scheduledInspection.cluster')}
                    rules={[{ required: true, message: t('scheduledInspection.selectCluster') }]}
                  >
                    <Select placeholder={t('scheduledInspection.selectCluster')}>
                      {clusters.map(cluster => (
                        <Option key={cluster.name} value={cluster.name}>
                          {cluster.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item
                    name="schedule_type"
                    label={t('scheduledInspection.scheduleType')}
                    rules={[{ required: true, message: t('scheduledInspection.selectScheduleType') }]}
                  >
                    <Select placeholder={t('scheduledInspection.selectScheduleType')}>
                      <Option value="cron">{t('scheduledInspection.periodicCron')}</Option>
                      <Option value="once">{t('scheduledInspection.oneTime')}</Option>
                    </Select>
                  </Form.Item>

                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) =>
                      prevValues.schedule_type !== currentValues.schedule_type
                    }
                  >
                    {({ getFieldValue }) => {
                      const scheduleType = getFieldValue('schedule_type');
                      if (scheduleType === 'cron') {
                        return (
                          <div>
                            <Alert
                              message={t('scheduledInspection.cronFormat')}
                              type="info"
                              showIcon
                              className="margin-bottom-space-4"
                            />
                            <Space wrap>
                              <Form.Item name="cron_min" label={t('scheduledInspection.minutes')} initialValue="0">
                                <Input placeholder="0" />
                              </Form.Item>
                              <Form.Item name="cron_hour" label={t('scheduledInspection.hours')} initialValue="8">
                                <Input placeholder="8" />
                              </Form.Item>
                              <Form.Item name="cron_dom" label={t('scheduledInspection.dayOfMonth')} initialValue="*">
                                <Input placeholder="*" />
                              </Form.Item>
                              <Form.Item name="cron_month" label={t('scheduledInspection.month')} initialValue="*">
                                <Input placeholder="*" />
                              </Form.Item>
                              <Form.Item name="cron_dow" label={t('scheduledInspection.dayOfWeek')} initialValue="*">
                                <Input placeholder="*" />
                              </Form.Item>
                            </Space>
                          </div>
                        );
                      } else if (scheduleType === 'once') {
                        return (
                          <Space>
                            <Form.Item
                              name="run_date"
                              label={t('scheduledInspection.runDate')}
                              rules={[{ required: true }]}
                            >
                              <DatePicker />
                            </Form.Item>
                            <Form.Item
                              name="run_time"
                              label={t('scheduledInspection.runTime')}
                              rules={[{ required: true }]}
                            >
                              <TimePicker format="HH:mm" />
                            </Form.Item>
                          </Space>
                        );
                      }
                      return null;
                    }}
                  </Form.Item>

                  <div className="margin-top-space-6 margin-bottom-space-6">
                    <h4>{t('scheduledInspection.selectInspectionRules')}</h4>
                    <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
                      <div style={{ flex: 1 }}>
                        <RuleSelector
                          ruleType="node"
                          title={t('scheduledInspection.nodeRules')}
                          availableRules={rules.node || []}
                          selectedRules={selectedRules}
                          onRuleSelection={handleRuleSelection}
                        />
                      </div>
                      <div style={{ flex: 1 }}>
                        <RuleSelector
                          ruleType="opa"
                          title={t('scheduledInspection.kubernetesRules')}
                          availableRules={rules.opa || []}
                          selectedRules={selectedRules}
                          onRuleSelection={handleRuleSelection}
                        />
                      </div>
                    </div>
                  </div>

                  <Form.Item
                    name="enabled"
                    label={t('scheduledInspection.enableTask')}
                    valuePropName="checked"
                    initialValue={true}
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item>
                    <Button type="primary" htmlType="submit">
                      {t('scheduledInspection.createTaskButton')}
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title={t('scheduledInspection.editTask')}
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingTask(null);
          editForm.resetFields();
          setSelectedRules({ node: [], opa: [] });
        }}
        footer={null}
        width={800}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdateTask}>
          <Form.Item
            name="name"
            label={t('scheduledInspection.taskName')}
            rules={[{ required: true, message: t('scheduledInspection.enterTaskName') }]}
          >
            <Input placeholder={t('scheduledInspection.dailyCheck')} />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('scheduledInspection.description')}
            rules={[{ required: true, message: t('scheduledInspection.enterDescription') }]}
          >
            <Input.TextArea placeholder={t('scheduledInspection.taskDescription')} />
          </Form.Item>

          <Form.Item
            name="cluster"
            label={t('scheduledInspection.cluster')}
            rules={[{ required: true, message: t('scheduledInspection.selectCluster') }]}
          >
            <Select placeholder={t('scheduledInspection.selectCluster')}>
              {clusters.map(cluster => (
                <Option key={cluster.name} value={cluster.name}>
                  {cluster.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="schedule_type"
            label={t('scheduledInspection.scheduleType')}
            rules={[{ required: true, message: t('scheduledInspection.selectScheduleType') }]}
          >
            <Select placeholder={t('scheduledInspection.selectScheduleType')}>
              <Option value="cron">{t('scheduledInspection.periodicCron')}</Option>
              <Option value="once">{t('scheduledInspection.oneTime')}</Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.schedule_type !== currentValues.schedule_type
            }
          >
            {({ getFieldValue }) => {
              const scheduleType = getFieldValue('schedule_type');
              if (scheduleType === 'cron') {
                return (
                  <div>
                    <Alert
                      message={t('scheduledInspection.cronFormat')}
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    <Space wrap>
                      <Form.Item name="cron_min" label={t('scheduledInspection.minutes')} initialValue="0">
                        <Input placeholder="0" />
                      </Form.Item>
                      <Form.Item name="cron_hour" label={t('scheduledInspection.hours')} initialValue="8">
                        <Input placeholder="8" />
                      </Form.Item>
                      <Form.Item name="cron_dom" label={t('scheduledInspection.dayOfMonth')} initialValue="*">
                        <Input placeholder="*" />
                      </Form.Item>
                      <Form.Item name="cron_month" label={t('scheduledInspection.month')} initialValue="*">
                        <Input placeholder="*" />
                      </Form.Item>
                      <Form.Item name="cron_dow" label={t('scheduledInspection.dayOfWeek')} initialValue="*">
                        <Input placeholder="*" />
                      </Form.Item>
                    </Space>
                  </div>
                );
              } else if (scheduleType === 'once') {
                return (
                  <Space>
                    <Form.Item name="run_date" label={t('scheduledInspection.runDate')} rules={[{ required: true }]}>
                      <DatePicker />
                    </Form.Item>
                    <Form.Item
                      name="run_time"
                      label={t('scheduledInspection.runTime')}
                      rules={[{ required: true }]}
                    >
                      <TimePicker format="HH:mm" />
                    </Form.Item>
                  </Space>
                );
              }
              return null;
            }}
          </Form.Item>

          <div className="margin-top-space-6 margin-bottom-space-6">
            <h4>{t('scheduledInspection.selectInspectionRules')}</h4>
            <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
              <div style={{ flex: 1 }}>
                <RuleSelector
                  ruleType="node"
                  title={t('scheduledInspection.nodeRules')}
                  availableRules={rules.node || []}
                  selectedRules={selectedRules}
                  onRuleSelection={handleRuleSelection}
                />
              </div>
              <div style={{ flex: 1 }}>
                <RuleSelector
                  ruleType="opa"
                  title={t('scheduledInspection.kubernetesRules')}
                  availableRules={rules.opa || []}
                  selectedRules={selectedRules}
                  onRuleSelection={handleRuleSelection}
                />
              </div>
            </div>
          </div>

          <Form.Item
            name="enabled"
            label={t('scheduledInspection.enableTask')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit">
              {t('scheduledInspection.updateTask')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ScheduledInspection;
