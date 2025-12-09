import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Tabs, message, Space, Tag, Collapse } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { getClusters, createCluster, updateCluster, deleteCluster, getClusterDetails, testClusterNodes, testClusterKubeconfig } from '../services/api';

const { TabPane } = Tabs;

const ClusterManagement = () => {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const loadClusters = async () => {
    try {
      setLoading(true);
      const response = await getClusters();
      setClusters(response.data.clusters || []);
    } catch (error) {
      message.error('Ошибка загрузки кластеров');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClusters();
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      // Загрузка деталей кластера для редактирования
      loadClusterDetails(selectedCluster.name);
    }
  }, [selectedCluster]);

  const handleCreateCluster = async (values) => {
    try {
      // Парсинг узлов из текста
      const nodes = parseNodesFromText(values.nodes_text);
      const clusterData = {
        name: values.name,
        nodes: nodes,
        prometheus_config: values.prometheus_enabled ? {
          enabled: true,
          url: values.prometheus_url,
          username: values.prometheus_username,
          password: values.prometheus_password
        } : { enabled: false },
        kubeconfig: values.kubeconfig
      };

      await createCluster(clusterData);
      message.success('Кластер создан успешно');
      setCreateModalVisible(false);
      form.resetFields();
      loadClusters();
    } catch (error) {
      message.error('Ошибка создания кластера');
      console.error(error);
    }
  };

  const handleDeleteCluster = async (clusterName) => {
    try {
      await deleteCluster(clusterName);
      message.success('Кластер удален');
      loadClusters();
    } catch (error) {
      message.error('Ошибка удаления кластера');
      console.error(error);
    }
  };

  const loadClusterDetails = async (clusterName) => {
    try {
      const response = await getClusterDetails(clusterName);
      const clusterData = response.data;

      // Преобразование данных для формы
      const formData = {
        name: clusterData.name,
        nodes_text: formatNodesForText(clusterData.nodes),
        prometheus_enabled: clusterData.prometheus_config?.enabled || false,
        prometheus_url: clusterData.prometheus_config?.url || '',
        prometheus_username: clusterData.prometheus_config?.username || '',
        prometheus_password: clusterData.prometheus_config?.password || '',
        kubeconfig: clusterData.kubeconfig || ''
      };

      editForm.setFieldsValue(formData);
      setEditModalVisible(true);
    } catch (error) {
      message.error('Ошибка загрузки данных кластера');
      console.error(error);
      setSelectedCluster(null);
    }
  };

  const handleEditCluster = async (values) => {
    try {
      // Парсинг узлов из текста
      const nodes = parseNodesFromText(values.nodes_text);
      const clusterData = {
        name: values.name,
        nodes: nodes,
        prometheus_config: values.prometheus_enabled ? {
          enabled: true,
          url: values.prometheus_url,
          username: values.prometheus_username,
          password: values.prometheus_password
        } : { enabled: false },
        kubeconfig: values.kubeconfig
      };

      await updateCluster(selectedCluster.name, clusterData);
      message.success('Кластер обновлен успешно');

      setEditModalVisible(false);
      setSelectedCluster(null);
      editForm.resetFields();
      loadClusters();
    } catch (error) {
      message.error('Ошибка обновления кластера');
      console.error(error);
    }
  };

  const handleTestNodes = async () => {
    let nodesToTest = null;
    let clusterName = selectedCluster?.name;

    try {

      if (editModalVisible && editForm) {
        const formValues = editForm.getFieldsValue();
        nodesToTest = parseNodesFromText(formValues.nodes_text || '');
      } else if (form) {
        // For add cluster tab
        const formValues = form.getFieldsValue();
        nodesToTest = parseNodesFromText(formValues.nodes_text || '');
        clusterName = null; // No cluster yet
      }

      const response = await testClusterNodes(clusterName, nodesToTest);
      const results = response.data.results;

      let successCount = 0;
      let failCount = 0;
      const failedNodes = [];

      results.forEach(result => {
        if (result.success) {
          successCount++;
        } else {
          failCount++;
          failedNodes.push(result.node_name || result.node);
        }
      });

      if (failCount > 0) {
        const failedList = failedNodes.join(', ');
        message.error(`Не удалось подключиться: ${failedList}`);
      } else if (results.length > 0) {
        message.success(`Все узлы доступны (${successCount} успешно)`);
      } else {
        message.warning('Не получено результатов тестирования');
      }
    } catch (error) {
      let errorMessage = 'Неизвестная ошибка';

      // Debug: log the full error structure
      console.error('Full error object:', error);
      console.error('Error response:', error.response);
      console.error('Error response data:', error.response?.data);

      if (error.response?.data) {
        const data = error.response.data;
        if (typeof data === 'string') {
          errorMessage = data;
        } else if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (typeof data.detail === 'object') {
            errorMessage = data.detail.message || data.detail.error || JSON.stringify(data.detail);
          } else {
            errorMessage = String(data.detail);
          }
        } else if (data.message) {
          errorMessage = data.message;
        } else if (data.error) {
          errorMessage = data.error;
        } else {
          // If data is an object but has no known fields, stringify it
          errorMessage = JSON.stringify(data);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      const failedNodes = nodesToTest ? nodesToTest.map(node => `${node.ip}:${node.port}`).join(', ') : 'неизвестные узлы';
      message.error(`Ошибка проверки узлов: ${errorMessage}`);
    }
  };

  const handleTestKubeconfig = async () => {
    try {
      let kubeconfigToTest = null;
      let clusterName = selectedCluster?.name;

      if (editModalVisible && editForm) {
        const formValues = editForm.getFieldsValue();
        kubeconfigToTest = formValues.kubeconfig;
      } else if (form) {
        // For add cluster tab
        const formValues = form.getFieldsValue();
        kubeconfigToTest = formValues.kubeconfig;
        clusterName = null; // No cluster yet
      }

      const response = await testClusterKubeconfig(clusterName, kubeconfigToTest);
      const { success, message: testMessage } = response.data;

      Modal.info({
        title: 'Результаты проверки kubeconfig',
        content: (
          <div>
            <div style={{ marginBottom: 16 }}>
              {success ? '✅' : '❌'} {testMessage}
            </div>
          </div>
        ),
        width: 500,
      });
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Неизвестная ошибка';
      message.error(`Ошибка проверки kubeconfig: ${errorMessage}`);
      console.error(error);
    }
  };

  const parseNodesFromText = (text) => {
    const nodes = [];
    const lines = text.split('\n').filter(line => line.trim());

    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 3) {
        const [ip_port, user, auth_type, ...auth_data] = parts;
        const [ip, port_str] = ip_port.split(':');
        const port = parseInt(port_str) || 22;
        const auth_data_str = auth_data.join(' ') || '';

        const node = {
          ip,
          port,
          username: user,
          auth_type
        };

        if (auth_type === 'password') {
          node.password = auth_data_str;
        } else if (auth_type === 'key') {
          node.key_path = auth_data_str;
        }

        nodes.push(node);
      }
    }

    return nodes;
  };

  const formatNodesForText = (nodes) => {
    return nodes.map(node => {
      const ip_port = `${node.ip}:${node.port}`;
      const auth_data = node.auth_type === 'password' ? node.password : node.key_path;
      return `${ip_port} ${node.username} ${node.auth_type} ${auth_data || ''}`.trim();
    }).join('\n');
  };

  const clusterColumns = [
    { title: 'Имя кластера', dataIndex: 'name', key: 'name' },
    { title: 'Узлы', dataIndex: 'nodes', key: 'nodes', render: (nodes) => nodes?.length || 0 },
    { title: 'Prometheus', dataIndex: 'prometheus_config', key: 'prometheus', render: (config) => config?.enabled ? <Tag color="#50fa7b">Включен</Tag> : <Tag color="#ff5555">Отключен</Tag> },
    { title: 'Kubeconfig', dataIndex: 'kubeconfig', key: 'kubeconfig', render: (kubeconfig) => kubeconfig ? <Tag color="#50fa7b">Настроен</Tag> : <Tag color="#ff5555">Не настроен</Tag> },
    {
      title: 'Сертификат истекает через',
      dataIndex: 'cert_expiry_days',
      key: 'cert_expiry',
      render: (days) => {
        if (days === null || days === undefined) {
          return <Tag color="#6272a4">Неизвестно</Tag>;
        }
        if (days < 0) {
          return <Tag color="#ff5555">Истек</Tag>;
        }
        if (days <= 7) {
          return <Tag color="#ff5555">{days} дней</Tag>;
        }
        if (days <= 30) {
          return <Tag color="#f1fa8c">{days} дней</Tag>;
        }
        return <Tag color="#50fa7b">{days} дней</Tag>;
      }
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => setSelectedCluster(record)}>
            Редактировать
          </Button>
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={() => Modal.confirm({
              title: 'Удалить кластер?',
              content: `Вы уверены, что хотите удалить кластер ${record.name}?`,
              onOk: () => handleDeleteCluster(record.name)
            })}
          >
            Удалить
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div>
      <div className="page-title">Управление кластерами</div>
      <div className="page-subtitle">Настройка подключений к Kubernetes кластерам</div>

      <Tabs defaultActiveKey="1">
        <TabPane tab="Список кластеров" key="1">
          <Card>
            <Table
              columns={clusterColumns}
              dataSource={clusters}
              loading={loading}
              rowKey="name"
            />
          </Card>
        </TabPane>

        <TabPane tab="Добавить кластер" key="2">
          <Card>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleCreateCluster}
            >
              <Form.Item
                name="name"
                label="Имя кластера"
                rules={[{ required: true, message: 'Введите имя кластера' }]}
              >
                <Input placeholder="production" />
              </Form.Item>

              <Form.Item
                name="nodes_text"
                label="Список узлов"
                rules={[{ required: true, message: 'Добавьте хотя бы один узел' }]}
              >
                <Input.TextArea
                  rows={6}
                  placeholder={`Добавьте SSH узлы для проверки в формате: IP:Port User AuthType [Password/KeyPath]
Примеры:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa`}
                />
              </Form.Item>

              <Collapse defaultActiveKey={[]}>
                <Collapse.Panel header="Настройки Prometheus" key="prometheus">
                  <Form.Item
                    name="prometheus_enabled"
                    label="Включить Prometheus"
                    valuePropName="checked"
                  >
                    <input type="checkbox" />
                  </Form.Item>

                  <Form.Item
                    name="prometheus_url"
                    label="URL Prometheus"
                  >
                    <Input placeholder="http://prometheus.example.com:9090" />
                  </Form.Item>

                  <Form.Item
                    name="prometheus_username"
                    label="Имя пользователя Prometheus"
                  >
                    <Input />
                  </Form.Item>

                  <Form.Item
                    name="prometheus_password"
                    label="Пароль Prometheus"
                  >
                    <Input.Password />
                  </Form.Item>
                </Collapse.Panel>
              </Collapse>

              <Form.Item
                name="kubeconfig"
                label="Kubeconfig"
                rules={[{ required: true, message: 'Введите kubeconfig' }]}
              >
                <Input.TextArea
                  rows={8}
                  placeholder="Вставьте содержимое kubeconfig файла"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit">
                    Создать кластер
                  </Button>
                  <Button onClick={handleTestNodes}>
                    Проверить узлы
                  </Button>
                  <Button onClick={handleTestKubeconfig}>
                    Проверить kubeconfig
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>

      <Modal
        title="Создать кластер"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateCluster}
        >
          <Form.Item
            name="name"
            label="Имя кластера"
            rules={[{ required: true, message: 'Введите имя кластера' }]}
          >
            <Input placeholder="production" />
          </Form.Item>

          <Form.Item
            name="nodes_text"
            label="Список узлов"
            rules={[{ required: true, message: 'Добавьте хотя бы один узел' }]}
          >
            <Input.TextArea
              rows={6}
              placeholder={`Добавьте SSH узлы для проверки в формате: IP:Port User AuthType [Password/KeyPath]
Примеры:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa`}
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit">
              Создать кластер
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Редактировать кластер: ${selectedCluster?.name}`}
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setSelectedCluster(null);
          editForm.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditCluster}
        >
          <Form.Item
            name="name"
            label="Имя кластера"
            rules={[{ required: true, message: 'Введите имя кластера' }]}
          >
            <Input placeholder="production" />
          </Form.Item>

          <Form.Item
            name="nodes_text"
            label="Список узлов"
            rules={[{ required: true, message: 'Добавьте хотя бы один узел' }]}
          >
            <Input.TextArea
              rows={6}
              placeholder={`Добавьте SSH узлы для проверки в формате: IP:Port User AuthType [Password/KeyPath]
Примеры:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa`}
            />
          </Form.Item>

          <Collapse defaultActiveKey={[]}>
            <Collapse.Panel header="Настройки Prometheus" key="prometheus">
              <Form.Item
                name="prometheus_enabled"
                label="Включить Prometheus"
                valuePropName="checked"
              >
                <input type="checkbox" />
              </Form.Item>

              <Form.Item
                name="prometheus_url"
                label="URL Prometheus"
              >
                <Input placeholder="http://prometheus.example.com:9090" />
              </Form.Item>

              <Form.Item
                name="prometheus_username"
                label="Имя пользователя Prometheus"
              >
                <Input />
              </Form.Item>

              <Form.Item
                name="prometheus_password"
                label="Пароль Prometheus"
              >
                <Input.Password />
              </Form.Item>
            </Collapse.Panel>
          </Collapse>

          <Form.Item
            name="kubeconfig"
            label="Kubeconfig"
          >
            <Input.TextArea
              rows={8}
              placeholder="Вставьте содержимое kubeconfig файла"
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Обновить кластер
              </Button>
              <Button onClick={handleTestNodes}>
                Проверить узлы
              </Button>
              <Button onClick={handleTestKubeconfig}>
                Проверить kubeconfig
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ClusterManagement;