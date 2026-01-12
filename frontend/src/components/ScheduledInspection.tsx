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
import {
  getClusters,
  getRules,
  getScheduledTasks,
  createScheduledTask,
  deleteScheduledTask,
  runScheduledTask,
  updateScheduledTask,
} from '../services/api';
import RuleSelector from './RuleSelector';
import { getStatusTag } from './statusUtils';

const { Option } = Select;
const { TabPane } = Tabs;

const ScheduledInspection = () => {
  const [tasks, setTasks] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [rules, setRules] = useState({});
  const [loading, setLoading] = useState(true);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [selectedRules, setSelectedRules] = useState({ node: [], opa: [] });
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const handleRuleSelection = (ruleType, ruleIds) => {
    setSelectedRules(prev => ({
      ...prev,
      [ruleType]: ruleIds,
    }));
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [tasksRes, clustersRes, rulesRes] = await Promise.all([
        getScheduledTasks(),
        getClusters(),
        getRules(),
      ]);
      setTasks(tasksRes.data.tasks || []);
      setClusters(clustersRes.data.clusters || []);
      setRules(rulesRes.data.rules || {});
    } catch (error) {
      message.error('Ошибка загрузки данных');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateTask = async values => {
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

      await createScheduledTask(taskData);
      message.success('Задача создана успешно');
      form.resetFields();
      setSelectedRules({ node: [], opa: [] });
      loadData();
    } catch (error) {
      message.error('Ошибка создания задачи');
      console.error(error);
    }
  };

  const handleDeleteTask = async taskId => {
    try {
      await deleteScheduledTask(taskId);
      message.success('Задача удалена');
      loadData();
    } catch (error) {
      message.error('Ошибка удаления задачи');
      console.error(error);
    }
  };

  const handleRunTask = async taskId => {
    try {
      await runScheduledTask(taskId);
      message.success('Задача запущена');
      loadData();
    } catch (error) {
      message.error('Ошибка запуска задачи');
      console.error(error);
    }
  };

  const handleEditTask = task => {
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

  const handleUpdateTask = async values => {
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

      await updateScheduledTask(editingTask.task_id, taskData);
      message.success('Задача обновлена успешно');
      setEditModalVisible(false);
      setEditingTask(null);
      editForm.resetFields();
      setSelectedRules({ node: [], opa: [] });
      loadData();
    } catch (error) {
      message.error('Ошибка обновления задачи');
      console.error(error);
    }
  };

  const taskColumns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Кластер', dataIndex: 'cluster', key: 'cluster' },
    {
      title: 'Расписание',
      dataIndex: 'cron_expr',
      key: 'cron_expr',
      render: (cron, record) => (record.task_type === 'once' ? 'Одноразовая' : cron),
    },
    { title: 'Статус', dataIndex: 'last_status', key: 'last_status', render: getStatusTag },
    {
      title: 'Включена',
      dataIndex: 'enabled',
      key: 'enabled',
      render: enabled => <Switch checked={enabled} disabled />,
    },
    {
      title: 'Последний запуск',
      dataIndex: 'last_run',
      key: 'last_run',
      render: date => (date ? new Date(date).toLocaleString() : 'Не запускался'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            icon={<PlayCircleFilled />}
            onClick={() => handleRunTask(record.task_id)}
            title="Запустить сейчас"
          />
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditTask(record)}
            title="Редактировать"
          />
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={() =>
              Modal.confirm({
                title: 'Удалить задачу?',
                content: 'Это действие нельзя отменить',
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
      <Tabs defaultActiveKey="1">
        <TabPane tab="Список задач" key="1">
          <Card>
            <Table
              columns={taskColumns}
              dataSource={tasks}
              loading={loading}
              rowKey="task_id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="Создать задачу" key="2">
          <Card>
            <Form form={form} layout="vertical" onFinish={handleCreateTask}>
              <Form.Item
                name="name"
                label="Название задачи"
                rules={[{ required: true, message: 'Введите название задачи' }]}
              >
                <Input placeholder="Ежедневная проверка" />
              </Form.Item>

              <Form.Item
                name="description"
                label="Описание"
                rules={[{ required: true, message: 'Введите описание задачи' }]}
              >
                <Input.TextArea placeholder="Описание задачи" />
              </Form.Item>

              <Form.Item
                name="cluster"
                label="Кластер"
                rules={[{ required: true, message: 'Выберите кластер' }]}
              >
                <Select placeholder="Выберите кластер">
                  {clusters.map(cluster => (
                    <Option key={cluster.name} value={cluster.name}>
                      {cluster.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="schedule_type"
                label="Тип расписания"
                rules={[{ required: true, message: 'Выберите тип расписания' }]}
              >
                <Select placeholder="Выберите тип">
                  <Option value="cron">Периодическая (Cron)</Option>
                  <Option value="once">Одноразовая</Option>
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
                          message="Cron формат: мин час день месяц день_недели"
                          type="info"
                          showIcon
                          className="margin-bottom-space-4"
                        />
                        <Space wrap>
                          <Form.Item name="cron_min" label="Минуты" initialValue="0">
                            <Input placeholder="0" />
                          </Form.Item>
                          <Form.Item name="cron_hour" label="Часы" initialValue="8">
                            <Input placeholder="8" />
                          </Form.Item>
                          <Form.Item name="cron_dom" label="День месяца" initialValue="*">
                            <Input placeholder="*" />
                          </Form.Item>
                          <Form.Item name="cron_month" label="Месяц" initialValue="*">
                            <Input placeholder="*" />
                          </Form.Item>
                          <Form.Item name="cron_dow" label="День недели" initialValue="*">
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
                          label="Дата выполнения"
                          rules={[{ required: true }]}
                        >
                          <DatePicker />
                        </Form.Item>
                        <Form.Item
                          name="run_time"
                          label="Время выполнения"
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
                <h4>Выберите правила инспекции:</h4>
                <div className="grid-auto-fit">
                  <RuleSelector
                    ruleType="node"
                    title="Правила узлов"
                    availableRules={rules.node || []}
                    selectedRules={selectedRules}
                    onRuleSelection={handleRuleSelection}
                  />
                  <RuleSelector
                    ruleType="opa"
                    title="Правила Kubernetes"
                    availableRules={rules.opa || []}
                    selectedRules={selectedRules}
                    onRuleSelection={handleRuleSelection}
                  />
                </div>
              </div>

              <Form.Item
                name="enabled"
                label="Включить задачу"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit">
                  Создать задачу
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>

      <Modal
        title="Редактировать задачу"
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
            label="Название задачи"
            rules={[{ required: true, message: 'Введите название задачи' }]}
          >
            <Input placeholder="Ежедневная проверка" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Описание"
            rules={[{ required: true, message: 'Введите описание задачи' }]}
          >
            <Input.TextArea placeholder="Описание задачи" />
          </Form.Item>

          <Form.Item
            name="cluster"
            label="Кластер"
            rules={[{ required: true, message: 'Выберите кластер' }]}
          >
            <Select placeholder="Выберите кластер">
              {clusters.map(cluster => (
                <Option key={cluster.name} value={cluster.name}>
                  {cluster.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="schedule_type"
            label="Тип расписания"
            rules={[{ required: true, message: 'Выберите тип расписания' }]}
          >
            <Select placeholder="Выберите тип">
              <Option value="cron">Периодическая (Cron)</Option>
              <Option value="once">Одноразовая</Option>
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
                      message="Cron формат: мин час день месяц день_недели"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    <Space wrap>
                      <Form.Item name="cron_min" label="Минуты" initialValue="0">
                        <Input placeholder="0" />
                      </Form.Item>
                      <Form.Item name="cron_hour" label="Часы" initialValue="8">
                        <Input placeholder="8" />
                      </Form.Item>
                      <Form.Item name="cron_dom" label="День месяца" initialValue="*">
                        <Input placeholder="*" />
                      </Form.Item>
                      <Form.Item name="cron_month" label="Месяц" initialValue="*">
                        <Input placeholder="*" />
                      </Form.Item>
                      <Form.Item name="cron_dow" label="День недели" initialValue="*">
                        <Input placeholder="*" />
                      </Form.Item>
                    </Space>
                  </div>
                );
              } else if (scheduleType === 'once') {
                return (
                  <Space>
                    <Form.Item name="run_date" label="Дата выполнения" rules={[{ required: true }]}>
                      <DatePicker />
                    </Form.Item>
                    <Form.Item
                      name="run_time"
                      label="Время выполнения"
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
            <h4>Выберите правила инспекции:</h4>
            <div className="grid-auto-fit">
              <RuleSelector
                ruleType="node"
                title="Правила узлов"
                availableRules={rules.node || []}
                selectedRules={selectedRules}
                onRuleSelection={handleRuleSelection}
              />
              <RuleSelector
                ruleType="opa"
                title="Правила Kubernetes"
                availableRules={rules.opa || []}
                selectedRules={selectedRules}
                onRuleSelection={handleRuleSelection}
              />
            </div>
          </div>

          <Form.Item
            name="enabled"
            label="Включить задачу"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit">
              Обновить задачу
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ScheduledInspection;
