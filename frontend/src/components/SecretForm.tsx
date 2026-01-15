/**
 * SecretForm component for creating and editing secrets
 */

import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Space, message, Card, Typography, Divider } from 'antd';
import { SaveOutlined, ClearOutlined } from '@ant-design/icons';
import { SecretType, SecretCreate, SecretUpdate } from '../types/secret';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface SecretFormProps {
  secretType: SecretType;
  initialValues?: Partial<SecretCreate>;
  onSubmit: (data: SecretCreate | SecretUpdate) => Promise<void>;
  onCancel?: () => void;
  loading?: boolean;
  mode?: 'create' | 'edit';
}

const SecretForm: React.FC<SecretFormProps> = ({
  secretType,
  initialValues,
  onSubmit,
  onCancel,
  loading = false,
  mode = 'create',
}) => {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues);
    }
  }, [initialValues, form]);

  const getTypeLabel = (type: SecretType): string => {
    switch (type) {
      case SecretType.PASSWORD:
        return 'Пароль';
      case SecretType.SSH_KEY:
        return 'SSH ключ';
      case SecretType.KUBECONFIG:
        return 'Kubeconfig';
      default:
        return type;
    }
  };

  const getTypePlaceholder = (type: SecretType): string => {
    switch (type) {
      case SecretType.PASSWORD:
        return 'Введите пароль';
      case SecretType.SSH_KEY:
        return '-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----';
      case SecretType.KUBECONFIG:
        return 'apiVersion: v1\nkind: Config\n...';
      default:
        return 'Введите данные';
    }
  };

  const getTypeHelp = (type: SecretType): string => {
    switch (type) {
      case SecretType.PASSWORD:
        return 'Пароль будет зашифрован и сохранен в базе данных';
      case SecretType.SSH_KEY:
        return 'Вставьте содержимое приватного SSH ключа';
      case SecretType.KUBECONFIG:
        return 'Вставьте содержимое kubeconfig файла';
      default:
        return '';
    }
  };

  const handleFinish = async (values: SecretCreate | SecretUpdate) => {
    setSubmitting(true);
    try {
      await onSubmit(values);
      message.success(mode === 'create' ? 'Секрет успешно создан' : 'Секрет успешно обновлен');
      form.resetFields();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || 'Ошибка при сохранении секрета');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    if (initialValues) {
      form.setFieldsValue(initialValues);
    }
  };

  return (
    <Card>
      <div>
        <Title level={4}>
          {mode === 'create' ? 'Создание' : 'Редактирование'}{' '}
          {getTypeLabel(secretType).toLowerCase()}
        </Title>
        <Text type="secondary">Все данные будут зашифрованы перед сохранением</Text>
      </div>

      <Divider />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{
          secret_type: secretType,
          ...initialValues,
        }}
      >
        <Form.Item
          label="Название"
          name="name"
          rules={[
            { required: true, message: 'Введите название секрета' },
            { max: 255, message: 'Название не должно превышать 255 символов' },
          ]}
        >
          <Input placeholder="Например: production-db-password" disabled={loading} />
        </Form.Item>

        <Form.Item label="Описание" name="description">
          <TextArea
            placeholder="Опишите назначение секрета (необязательно)"
            rows={2}
            disabled={loading}
          />
        </Form.Item>

        <Form.Item
          label={getTypeLabel(secretType)}
          name="data"
          rules={[{ required: true, message: `Введите ${getTypeLabel(secretType).toLowerCase()}` }]}
          help={getTypeHelp(secretType)}
        >
          {secretType === SecretType.PASSWORD ? (
            <Input.Password placeholder={getTypePlaceholder(secretType)} disabled={loading} />
          ) : (
            <TextArea placeholder={getTypePlaceholder(secretType)} rows={8} disabled={loading} />
          )}
        </Form.Item>

        <Form.Item>
          <Space wrap>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={submitting || loading}
            >
              {mode === 'create' ? 'Создать' : 'Сохранить'}
            </Button>
            <Button icon={<ClearOutlined />} onClick={handleReset} disabled={submitting || loading}>
              Сбросить
            </Button>
            {onCancel && (
              <Button onClick={onCancel} disabled={submitting || loading}>
                Отмена
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default SecretForm;
