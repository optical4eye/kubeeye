import React, { useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Tooltip,
  message,
  Popconfirm,
  Card,
  Typography,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  LockOutlined,
  KeyOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface Secret {
  id: number;
  name: string;
  secret_type: string;
  description: string | null;
  secret_metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
}

interface SecretFormData {
  name: string;
  secret_type: string;
  data: string;
  description: string;
  secret_metadata: Record<string, unknown>;
}

const SecretManagement: React.FC = () => {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null);
  const [revealModalVisible, setRevealModalVisible] = useState(false);
  const [revealedSecret, setRevealedSecret] = useState<{ data: string; secret: Secret } | null>(
    null
  );
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [form] = Form.useForm<SecretFormData>();

  const fetchSecrets = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/secrets');
      setSecrets(response.data.secrets);
    } catch {
      message.error('Не удалось загрузить секреты');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchSecrets();
  }, []);

  const handleCreate = () => {
    setModalMode('create');
    setSelectedSecret(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (secret: Secret) => {
    setModalMode('edit');
    setSelectedSecret(secret);
    form.setFieldsValue({
      name: secret.name,
      secret_type: secret.secret_type,
      description: secret.description || '',
      secret_metadata: secret.secret_metadata || {},
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await axios.delete(`/api/secrets/${id}`);
      message.success('Секрет успешно удален');
      fetchSecrets();
    } catch {
      message.error('Не удалось удалить секрет');
    }
  };

  const handleReveal = async (id: number) => {
    try {
      const response = await axios.post(`/api/secrets/${id}/reveal`);
      setRevealedSecret({
        data: response.data.data,
        secret: response.data,
      });
      setRevealModalVisible(true);
    } catch {
      message.error('Не удалось расшифровать секрет');
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();

      if (modalMode === 'create') {
        await axios.post('/api/secrets', values);
        message.success('Секрет успешно создан');
      } else {
        await axios.put(`/api/secrets/${selectedSecret!.id}`, values);
        message.success('Секрет успешно обновлен');
      }

      setModalVisible(false);
      form.resetFields();
      fetchSecrets();
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('Не удалось сохранить секрет');
      }
    }
  };

  const handleTest = async (id: number) => {
    try {
      const response = await axios.post(`/api/secrets/${id}/test`);
      if (response.data.success) {
        message.success(response.data.message);
      } else {
        message.error(response.data.message);
      }
    } catch {
      message.error('Не удалось проверить секрет');
    }
  };

  const getSecretTypeIcon = (type: string) => {
    switch (type) {
      case 'password':
        return <LockOutlined />;
      case 'ssh_key':
        return <KeyOutlined />;
      case 'kubeconfig':
        return <FileTextOutlined />;
      default:
        return <LockOutlined />;
    }
  };

  const getSecretTypeClass = (type: string) => {
    switch (type) {
      case 'password':
        return 'secret-type-password';
      case 'ssh_key':
        return 'secret-type-ssh-key';
      case 'kubeconfig':
        return 'secret-type-kubeconfig';
      default:
        return 'secret-type-default';
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Secret) => (
        <Space>
          {getSecretTypeIcon(record.secret_type)}
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'secret_type',
      key: 'secret_type',
      render: (type: string) => (
        <Tag icon={getSecretTypeIcon(type)} className={`secret-type-${type.replace('_', '-')}`}>
          {type}
        </Tag>
      ),
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      render: (text: string | null) => text || '-',
    },
    {
      title: 'Последнее использование',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      render: (date: string | null) => (date ? new Date(date).toLocaleString('ru-RU') : '-'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: Secret) => (
        <Space size="small" wrap>
           <Tooltip title="Просмотреть">
             <Button type="text" className="action-button" icon={<EyeOutlined />} onClick={() => handleReveal(record.id)} />
           </Tooltip>
           <Tooltip title="Проверить">
             <Button
               type="text"
               className="action-button"
               icon={<CheckCircleOutlined />}
               onClick={() => handleTest(record.id)}
             />
           </Tooltip>
           <Tooltip title="Редактировать">
             <Button type="text" className="action-button" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
           </Tooltip>
           <Popconfirm
             title="Вы уверены, что хотите удалить этот секрет?"
             onConfirm={() => handleDelete(record.id)}
             okText="Да"
             cancelText="Нет"
           >
             <Tooltip title="Удалить">
               <Button type="text" danger className="action-button" icon={<DeleteOutlined />} />
             </Tooltip>
           </Popconfirm>
         </Space>
      ),
    },
  ];

  return (
    <div className="secret-management">
      <div className="page-title">Управление секретами</div>
      <div className="page-subtitle">Управление секретами для подключения к кластерам</div>

      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Alert
            message="Безопасное хранение"
            description="Все секреты шифруются перед сохранением в базе данных. Пароли и ключи никогда не отображаются в открытом виде."
            type="info"
            showIcon
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Создать секрет
            </Button>
          </div>

          <Table
            columns={columns}
            dataSource={secrets}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: total => `Всего: ${total}`,
            }}
          />
        </Space>
      </Card>

      <Modal
        title={modalMode === 'create' ? 'Создать секрет' : 'Редактировать секрет'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        width={600}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical" autoComplete="off">
          <Form.Item
            label="Название"
            name="name"
            rules={[
              { required: true, message: 'Пожалуйста, введите название' },
              { min: 3, message: 'Название должно содержать минимум 3 символа' },
              { max: 100, message: 'Название не должно превышать 100 символов' },
            ]}
          >
            <Input placeholder="Уникальное название секрета" />
          </Form.Item>

          <Form.Item
            label="Тип секрета"
            name="secret_type"
            rules={[{ required: true, message: 'Пожалуйста, выберите тип' }]}
          >
            <Select placeholder="Выберите тип секрета">
              <Option value="password">Пароль</Option>
              <Option value="ssh_key">SSH ключ</Option>
              <Option value="kubeconfig">Kubeconfig</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="Данные"
            name="data"
            rules={[
              { required: true, message: 'Пожалуйста, введите данные' },
              {
                validator: (_, value) => {
                  if (!value || !value.trim()) {
                    return Promise.reject('Данные не могут быть пустыми');
                  }
                  return Promise.resolve();
                },
              },
            ]}
          >
            <TextArea
              rows={6}
              placeholder="Введите данные секрета"
              type={passwordVisible ? 'text' : 'password'}
              suffix={
                <Button
                  type="text"
                  icon={passwordVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                  onClick={() => setPasswordVisible(!passwordVisible)}
                />
              }
            />
          </Form.Item>

          <Form.Item label="Описание" name="description">
            <TextArea rows={3} placeholder="Необязательное описание" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Просмотр секрета"
        open={revealModalVisible}
        onCancel={() => {
          setRevealModalVisible(false);
          setRevealedSecret(null);
        }}
        footer={[
          <Button key="close" onClick={() => setRevealModalVisible(false)}>
            Закрыть
          </Button>,
        ]}
        width={700}
      >
        {revealedSecret && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Text strong>Название:</Text>
              <div>{revealedSecret.secret.name}</div>
            </div>
            <div>
              <Text strong>Тип:</Text>
              <div>
                <Tag
                  className={`secret-type-tag ${getSecretTypeClass(revealedSecret.secret.secret_type)}`}
                >
                  {revealedSecret.secret.secret_type}
                </Tag>
              </div>
            </div>
            <div>
              <Text strong>Данные:</Text>
              <div style={{ marginTop: '8px' }}>
                <TextArea
                  value={revealedSecret.data}
                  rows={10}
                  readOnly
                  style={{ fontFamily: 'monospace' }}
                />
              </div>
            </div>
            <Alert
              message="Предупреждение"
              description="Эти данные чувствительны. Не делитесь ими и не сохраняйте в небезопасных местах."
              type="warning"
              showIcon
            />
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default SecretManagement;
