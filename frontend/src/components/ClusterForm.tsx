import React, { useState } from 'react';
import { Form, Input, Button, Space, Modal, Tag, Tooltip, Table } from 'antd';
import { KeyOutlined, InfoCircleOutlined, LockOutlined, FileTextOutlined } from '@ant-design/icons';
import axios from 'axios';

const ClusterForm = ({
  form,
  onSubmit,
  onTestNodes,
  onTestKubeconfig,
  onGetNodesFromKubeconfig,
  isEditMode = false,
}) => {
  const [secretModalVisible, setSecretModalVisible] = useState(false);
  const [secrets, setSecrets] = useState([]);
  const [targetField, setTargetField] = useState(null);

  const loadSecrets = async () => {
    try {
      const response = await axios.get('/api/secrets');
      setSecrets(response.data.secrets || []);
    } catch (error) {
      console.error('Failed to load secrets:', error);
    }
  };

  const openSecretModal = fieldName => {
    setTargetField(fieldName);
    loadSecrets();
    setSecretModalVisible(true);
  };

  const selectSecret = secretName => {
    const secretVariable = `\u0024\u007Bsecret:${secretName}\u007D`;
    const currentValue = form.getFieldValue(targetField) || '';
    form.setFieldValue(targetField, currentValue + secretVariable);
    setSecretModalVisible(false);
  };

  const getSecretTypeIcon = type => {
    switch (type) {
      case 'password':
        return (
          <Tag className="secret-type-password" icon={<LockOutlined />}>
            password
          </Tag>
        );
      case 'ssh_key':
        return (
          <Tag className="secret-type-ssh-key" icon={<KeyOutlined />}>
            ssh_key
          </Tag>
        );
      case 'kubeconfig':
        return (
          <Tag className="secret-type-kubeconfig" icon={<FileTextOutlined />}>
            kubeconfig
          </Tag>
        );
      default:
        return <Tag>{type}</Tag>;
    }
  };

  return (
    <>
      <Form
        form={form}
        layout="vertical"
        onFinish={onSubmit}
        aria-label={isEditMode ? 'Форма редактирования кластера' : 'Форма создания кластера'}
      >
        <Form.Item
          name="name"
          label="Имя кластера"
          rules={[{ required: true, message: 'Введите имя кластера' }]}
        >
          <Input placeholder="production" aria-label="Имя кластера" />
        </Form.Item>

        <Form.Item
          name="nodes_text"
          label={
            <Space>
              <span>Список узлов</span>
            </Space>
          }
          rules={[{ required: true, message: 'Добавьте хотя бы один узел' }]}
        >
          <Input.TextArea
            rows={6}
            placeholder={
              'Добавьте SSH узлы для проверки в формате: IP:Port User AuthType ${secret:имя-секрета}\nПримеры:\n192.168.1.100:22 root password ${secret:имя-секрета}\n192.168.1.101:22 admin key ${secret:имя-секрета}'
            }
            aria-label="Список узлов в формате IP:Port User AuthType ${secret:имя-секрета}"
          />
        </Form.Item>

        <Form.Item>
          <Space wrap>
            <Button
              className="action-button"
              icon={<KeyOutlined />}
              onClick={() => openSecretModal('nodes_text')}
              aria-label="Вставить секрет в список узлов"
            >
              Вставить секрет в узлы
            </Button>
            <Button
              className="action-button"
              onClick={onGetNodesFromKubeconfig}
              aria-label="Получить узлы из k8s"
            >
              Получить узлы из k8s
            </Button>
            <Button className="action-button" onClick={onTestNodes} aria-label="Проверить узлы">
              Проверить узлы
            </Button>
          </Space>
        </Form.Item>

        <Form.Item
          name="kubeconfig"
          label={
            <Space>
              <span>Kubeconfig</span>
              <Tooltip title="Используйте переменную ${secret:имя-секрета} для kubeconfig">
                <InfoCircleOutlined style={{ color: 'var(--info-color)' }} />
              </Tooltip>
            </Space>
          }
          rules={isEditMode ? [] : [{ required: true, message: 'Введите kubeconfig' }]}
        >
          <Input.TextArea
            rows={8}
            placeholder="${secret:имя-секрета}"
            aria-label="Содержимое kubeconfig файла"
          />
        </Form.Item>

        <Form.Item>
          <Space wrap>
            <Button
              className="action-button"
              icon={<KeyOutlined />}
              onClick={() => openSecretModal('kubeconfig')}
              aria-label="Вставить секрет в kubeconfig"
            >
              Вставить секрет в kubeconfig
            </Button>
            <Button
              className="action-button"
              onClick={onTestKubeconfig}
              aria-label="Проверить kubeconfig"
            >
              Проверить kubeconfig
            </Button>
          </Space>
        </Form.Item>

        <Form.Item>
          <Button
            className="action-button"
            type="primary"
            htmlType="submit"
            aria-label={isEditMode ? 'Обновить кластер' : 'Создать кластер'}
          >
            {isEditMode ? 'Обновить кластер' : 'Создать кластер'}
          </Button>
        </Form.Item>
      </Form>

      <Modal
        title="Выберите секрет"
        open={secretModalVisible}
        onCancel={() => setSecretModalVisible(false)}
        footer={null}
        width={800}
      >
        <Table
          dataSource={secrets}
          rowKey="id"
          pagination={{ pageSize: 5 }}
          columns={[
            { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
            {
              title: 'Название',
              dataIndex: 'name',
              key: 'name',
            },
            {
              title: 'Тип',
              dataIndex: 'secret_type',
              key: 'secret_type',
              render: type => getSecretTypeIcon(type),
            },
            {
              title: 'Описание',
              dataIndex: 'description',
              key: 'description',
              render: text => text || '-',
            },
            {
              title: 'Действия',
              key: 'actions',
              render: (_, record) => (
                <Button
                  type="primary"
                  size="small"
                  className="action-button"
                  onClick={() => selectSecret(record.name)}
                  aria-label={`Выбрать секрет ${record.name}`}
                >
                  Выбрать
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: 'Нет доступных секретов' }}
        />
      </Modal>
    </>
  );
};

export default ClusterForm;
