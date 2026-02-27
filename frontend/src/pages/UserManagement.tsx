import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Space,
  Tag,
  Popconfirm,
  App,
  Flex,
} from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useUsers, User, UserUpdateData } from '../hooks/useUsers';
import { useAuthStore } from '../stores/authStore';
import { getAllRoles, getRoleLabel, getRoleColor } from '../config/rbac';
import { formatDateTimeRu } from '../utils/dateFormat';

const { Option } = Select;

const UserManagement: React.FC = () => {
  const { t } = useTranslation();
  const { users, loading, fetchUsers, updateUser, deleteUser } = useUsers();
  const { user: currentUser } = useAuthStore();
  const availableRoles = getAllRoles();
  const { message } = App.useApp();

  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
    });
    setIsModalVisible(true);
  };

  const handleDelete = async (userId: number, username: string) => {
    try {
      await deleteUser(userId);
      message.success(t('userManagement.userDeleted', { username }));
    } catch {
      // Error already handled in hook
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingUser) {
        // Update existing user
        const updateData: UserUpdateData = {
          email: values.email,
          role: values.role,
          is_active: values.is_active,
        };
        await updateUser(editingUser.id, updateData);
      }

      setIsModalVisible(false);
      form.resetFields();
    } catch {
      // Error already handled in hook
    }
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
  };

  const columns = [
    {
      title: t('userManagement.id'),
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: t('userManagement.username'),
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: t('userManagement.email'),
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: t('userManagement.role'),
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => <Tag color={getRoleColor(role)}>{getRoleLabel(role)}</Tag>,
    },
    {
      title: t('userManagement.authType'),
      dataIndex: 'auth_type',
      key: 'auth_type',
      render: (authType: string) => {
        const authTypeConfig: Record<string, { color: string; label: string }> = {
          ldap: { color: 'blue', label: 'LDAP' },
          oauth: { color: 'purple', label: 'OAuth' },
          local: { color: 'green', label: 'Local' },
        };
        const config = authTypeConfig[authType] || {
          color: 'default',
          label: authType || 'Unknown',
        };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: t('userManagement.isActive'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'default'}>
          {isActive ? t('userManagement.activeYes') : t('userManagement.activeNo')}
        </Tag>
      ),
    },
    {
      title: t('userManagement.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatDateTimeRu(date),
    },
    {
      title: t('userManagement.lastLoginAt'),
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string | undefined) =>
        date ? formatDateTimeRu(date) : t('userManagement.neverLoggedIn'),
    },
    {
      title: t('userManagement.actions'),
      key: 'actions',
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            disabled={record.id === currentUser?.id || record.auth_type === 'local'}
          >
            {t('userManagement.edit')}
          </Button>
          <Popconfirm
            title={t('userManagement.deleteConfirm')}
            description={t('userManagement.deleteConfirmText', { username: record.username })}
            onConfirm={() => handleDelete(record.id, record.username)}
            okText={t('userManagement.yes')}
            cancelText={t('userManagement.no')}
            disabled={record.id === currentUser?.id || record.auth_type === 'local'}
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              disabled={record.id === currentUser?.id || record.auth_type === 'local'}
            >
              {t('userManagement.delete')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Flex justify="flex-start" align="center" style={{ marginBottom: 16 }}>
        <h2>{t('userManagement.title')}</h2>
      </Flex>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: total => t('userManagement.totalUsers', { count: total }),
        }}
      />

      <Modal
        title={t('userManagement.editUser')}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        width={600}
        okText={t('userManagement.save')}
        cancelText={t('userManagement.cancel')}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            role: availableRoles[0],
            is_active: true,
          }}
        >
          <Form.Item
            label={t('userManagement.username')}
            name="username"
            rules={[
              { required: true, message: t('userManagement.usernameRequired') },
              { min: 3, message: t('userManagement.usernameMin') },
              { max: 50, message: t('userManagement.usernameMax') },
            ]}
          >
            <Input disabled={!!editingUser} placeholder={t('userManagement.usernamePlaceholder')} />
          </Form.Item>

          <Form.Item
            label={t('userManagement.email')}
            name="email"
            rules={[
              { required: true, message: t('userManagement.emailRequired') },
              { type: 'email', message: t('userManagement.emailInvalid') },
            ]}
          >
            <Input placeholder={t('userManagement.emailPlaceholder')} />
          </Form.Item>

          <Form.Item
            label={t('userManagement.role')}
            name="role"
            rules={[{ required: true, message: t('userManagement.roleRequired') }]}
          >
            <Select placeholder={t('userManagement.rolePlaceholder')}>
              {availableRoles.map(role => (
                <Option key={role} value={role}>
                  {getRoleLabel(role)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label={t('userManagement.isActive')} name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement;
