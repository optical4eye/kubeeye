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
  App,
  Popconfirm,
  Card,
  Alert,
  Statistic,
  Row,
  Col,
  Spin,
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
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import { getSecretTypeTag } from '../components/ui/statusUtils';
const { TextArea } = Input;

interface Secret {
  id: number;
  name: string;
  secret_type: string;
  description: string | null;
  secret_metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
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
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null);
  const [revealModalVisible, setRevealModalVisible] = useState(false);
  const [revealedSecret, setRevealedSecret] = useState<{ data: string; secret: Secret } | null>(
    null
  );
  const [revealLoading, setRevealLoading] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [form] = Form.useForm<SecretFormData>();

  const fetchSecrets = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/secrets');
      setSecrets(response.data.secrets);
    } catch {
      messageApi.error(t('secrets.messages.loadFailed'));
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
      await api.delete(`/api/secrets/${id}`);
      messageApi.success(t('secrets.messages.deleteSuccess'));
      fetchSecrets();
    } catch {
      messageApi.error(t('secrets.messages.deleteFailed'));
    }
  };

  const handleReveal = async (id: number) => {
    setRevealLoading(true);
    try {
      const response = await api.post(`/api/secrets/${id}/reveal`);
      setRevealedSecret({
        data: response.data.data,
        secret: response.data,
      });
      setRevealModalVisible(true);
    } catch {
      messageApi.error(t('secrets.messages.revealFailed'));
    } finally {
      setRevealLoading(false);
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();

      if (modalMode === 'create') {
        await api.post('/api/secrets', values);
        messageApi.success(t('secrets.messages.createSuccess'));
      } else {
        await api.put(`/api/secrets/${selectedSecret!.id}`, values);
        messageApi.success(t('secrets.messages.updateSuccess'));
      }

      setModalVisible(false);
      form.resetFields();
      fetchSecrets();
    } catch (error) {
      if (error instanceof Error) {
        messageApi.error(error.message);
      } else {
        messageApi.error(t('secrets.messages.saveFailed'));
      }
    }
  };

  const handleTest = async (id: number) => {
    try {
      const response = await api.post(`/api/secrets/${id}/test`);
      if (response.data.success) {
        messageApi.success(response.data.message);
      } else {
        messageApi.error(response.data.message);
      }
    } catch {
      messageApi.error(t('secrets.messages.testFailed'));
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

  const columns = [
    {
      title: t('secrets.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: t('secrets.columns.name'),
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
      title: t('secrets.columns.type'),
      dataIndex: 'secret_type',
      key: 'secret_type',
      render: (type: string) => getSecretTypeTag(type),
    },
    {
      title: t('secrets.columns.description'),
      dataIndex: 'description',
      key: 'description',
      render: (text: string | null) => text || '-',
    },
    {
      title: t('secrets.columns.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string | null) => (date ? new Date(date).toLocaleString('ru-RU') : '-'),
    },
    {
      title: t('secrets.columns.updated'),
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date: string | null) => (date ? new Date(date).toLocaleString('ru-RU') : '-'),
    },
    {
      title: t('secrets.columns.active'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? t('secrets.viewModal.yes') : t('secrets.viewModal.no')}
        </Tag>
      ),
    },
    {
      title: t('secrets.columns.lastUsed'),
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      render: (date: string | null) => (date ? new Date(date).toLocaleString('ru-RU') : '-'),
    },
    {
      title: t('secrets.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: Secret) => (
        <Space size="small" wrap>
          <Tooltip title={t('secrets.actions.view')}>
            <Button
              type="text"
              className="action-button"
              icon={<EyeOutlined />}
              onClick={() => handleReveal(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('secrets.actions.test')}>
            <Button
              type="text"
              className="action-button"
              icon={<CheckCircleOutlined />}
              onClick={() => handleTest(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('secrets.actions.edit')}>
            <Button
              type="text"
              className="action-button"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('secrets.confirm.delete')}
            onConfirm={() => handleDelete(record.id)}
            okText={t('secrets.confirm.yes')}
            cancelText={t('secrets.confirm.no')}
          >
            <Tooltip title={t('secrets.actions.delete')}>
              <Button type="text" danger className="action-button" icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="secret-management">
        <div className="page-title">{t('secrets.title')}</div>
        <div className="page-subtitle">{t('secrets.subtitle')}</div>

        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Alert
              message={t('secrets.secureStorage')}
              description={t('secrets.secureDescription')}
              type="info"
              showIcon
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                {t('secrets.createSecret')}
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
                showTotal: total => `${t('secrets.total')} ${total}`,
              }}
            />
          </Space>
        </Card>

        <Modal
          title={modalMode === 'create' ? t('secrets.modal.create') : t('secrets.modal.edit')}
          open={modalVisible}
          onOk={handleModalOk}
          onCancel={() => {
            setModalVisible(false);
            form.resetFields();
          }}
          width={600}
          okText={t('secrets.modal.save')}
          cancelText={t('secrets.modal.cancel')}
        >
          <Form form={form} layout="vertical" autoComplete="off">
            <Form.Item
              label={t('secrets.form.name')}
              name="name"
              rules={[
                { required: true, message: t('secrets.form.nameRequired') },
                { min: 3, message: t('secrets.form.nameMin') },
                { max: 100, message: t('secrets.form.nameMax') },
              ]}
            >
              <Input placeholder={t('secrets.form.namePlaceholder')} />
            </Form.Item>

            <Form.Item
              label={t('secrets.form.type')}
              name="secret_type"
              rules={[{ required: true, message: t('secrets.form.typeRequired') }]}
            >
              <Select
                placeholder={t('secrets.form.type')}
                options={[
                  { value: 'password', label: t('secrets.form.password') },
                  { value: 'ssh_key', label: t('secrets.form.sshKey') },
                  { value: 'kubeconfig', label: t('secrets.form.kubeconfig') },
                ]}
              />
            </Form.Item>

            <Form.Item
              label={t('secrets.form.data')}
              name="data"
              rules={[
                { required: true, message: t('secrets.form.dataRequired') },
                {
                  validator: (_, value) => {
                    if (!value || !value.trim()) {
                      return Promise.reject(t('secrets.form.dataEmpty'));
                    }
                    return Promise.resolve();
                  },
                },
              ]}
            >
              <TextArea
                rows={6}
                placeholder={t('secrets.form.dataPlaceholder')}
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

            <Form.Item label={t('secrets.form.description')} name="description">
              <TextArea rows={3} placeholder={t('secrets.form.descriptionPlaceholder')} />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title={t('secrets.viewModal.title')}
          open={revealModalVisible}
          onCancel={() => {
            setRevealModalVisible(false);
            setRevealedSecret(null);
          }}
          footer={[
            <Button key="close" onClick={() => setRevealModalVisible(false)}>
              {t('secrets.viewModal.close')}
            </Button>,
          ]}
          width="90vw"
        >
          {revealLoading ? (
            <Spin size="large" />
          ) : revealedSecret ? (
            <div>
              <Card title={t('secrets.viewModal.stats')} className="margin-bottom-space-4">
                <Row gutter={16}>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic
                      title={t('secrets.viewModal.dataLength')}
                      value={revealedSecret.data.length}
                    />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic
                      title={t('secrets.viewModal.lines')}
                      value={revealedSecret.data.split('\n').length}
                    />
                  </Col>
                </Row>
              </Card>

              <Card title={t('secrets.viewModal.secretData')}>
                <TextArea
                  value={revealedSecret.data}
                  rows={15}
                  readOnly
                  style={{ fontFamily: 'monospace', width: '100%' }}
                />
              </Card>

              <Alert
                message={t('secrets.viewModal.warning')}
                description={t('secrets.viewModal.warningDescription')}
                type="warning"
                showIcon
                className="margin-top-space-4"
              />
            </div>
          ) : null}
        </Modal>
      </div>
    </>
  );
};

export default SecretManagement;
