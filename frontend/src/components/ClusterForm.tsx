import React, { useState } from 'react';
import { Form, Input, Button, Space, Modal, List, Tag, Tooltip, Typography } from 'antd';
import { KeyOutlined, InfoCircleOutlined, LockOutlined, FileTextOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Text } = Typography;

const ClusterForm = ({ form, onSubmit, onTestNodes, onTestKubeconfig, isEditMode = false }) => {
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
          <Button
            icon={<KeyOutlined />}
            onClick={() => openSecretModal('nodes_text')}
            aria-label="Вставить секрет в список узлов"
          >
            Вставить секрет
          </Button>
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
          <Button
            icon={<KeyOutlined />}
            onClick={() => openSecretModal('kubeconfig')}
            aria-label="Вставить секрет в kubeconfig"
          >
            Вставить секрет
          </Button>
        </Form.Item>

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              aria-label={isEditMode ? 'Обновить кластер' : 'Создать кластер'}
            >
              {isEditMode ? 'Обновить кластер' : 'Создать кластер'}
            </Button>
            <Button onClick={onTestNodes} aria-label="Проверить узлы">
              Проверить узлы
            </Button>
            <Button onClick={onTestKubeconfig} aria-label="Проверить kubeconfig">
              Проверить kubeconfig
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Modal
        title="Выберите секрет"
        open={secretModalVisible}
        onCancel={() => setSecretModalVisible(false)}
        footer={null}
        width={600}
      >
        <List
          dataSource={secrets}
          renderItem={secret => (
            <List.Item
              actions={[
                <Button
                  key="select"
                  type="primary"
                  size="small"
                  onClick={() => selectSecret(secret.name)}
                  aria-label={`Выбрать секрет ${secret.name}`}
                >
                  Выбрать
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{secret.name}</Text>
                    {getSecretTypeIcon(secret.secret_type)}
                  </Space>
                }
                description={
                  <Space direction="vertical" size="small">
                    {secret.description && <Text type="secondary">{secret.description}</Text>}
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: 'Нет доступных секретов' }}
        />
      </Modal>
    </>
  );
};

export default ClusterForm;
