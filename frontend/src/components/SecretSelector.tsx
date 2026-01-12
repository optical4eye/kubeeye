/**
 * SecretSelector component for selecting saved secrets
 * Used in cluster configuration forms
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Select, Button, Space, Tooltip, message, Spin } from 'antd';
import { PlusOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { SecretType, Secret } from '../types/secret';
import { secretApi } from '../services/secretApi';
import './SecretSelector.css';

interface SecretSelectorProps {
  secretType: SecretType;
  value?: number | null;
  onChange?: (secretId: number | null) => void;
  disabled?: boolean;
  placeholder?: string;
  allowCreate?: boolean;
  onCreate?: () => void;
  allowReveal?: boolean;
  onReveal?: (secret: Secret) => void;
}

const SecretSelector: React.FC<SecretSelectorProps> = ({
  secretType,
  value,
  onChange,
  disabled = false,
  placeholder,
  allowCreate = true,
  onCreate,
  allowReveal = true,
  onReveal,
}) => {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null);

  const loadSecrets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await secretApi.getSecretsByType(secretType);
      setSecrets(data);

      // Set selected secret if value is provided
      if (value) {
        const secret = data.find(s => s.id === value);
        setSelectedSecret(secret || null);
      }
    } catch {
      message.error('Не удалось загрузить список секретов');
    } finally {
      setLoading(false);
    }
  }, [secretType, value]);

  useEffect(() => {
    loadSecrets();
  }, [loadSecrets]);

  const handleChange = (secretId: number | null) => {
    const secret = secrets.find(s => s.id === secretId);
    setSelectedSecret(secret || null);
    onChange?.(secretId);
  };

  const handleCreate = () => {
    if (onCreate) {
      onCreate();
    } else {
      message.info('Функция создания секрета будет доступна в следующей версии');
    }
  };

  const handleReveal = () => {
    if (selectedSecret && onReveal) {
      onReveal(selectedSecret);
    }
  };

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

  const defaultPlaceholder = placeholder || `Выберите ${getTypeLabel(secretType).toLowerCase()}`;

  return (
    <div className="secret-selector">
      <Space.Compact style={{ width: '100%' }}>
        <Select
          value={value}
          onChange={handleChange}
          disabled={disabled || loading}
          placeholder={defaultPlaceholder}
          loading={loading}
          style={{ flex: 1 }}
          allowClear
          showSearch
          optionFilterProp="children"
          notFoundContent={loading ? <Spin size="small" /> : 'Нет сохраненных секретов'}
        >
          {secrets.map(secret => (
            <Select.Option key={secret.id} value={secret.id}>
              <div className="secret-option">
                <span className="secret-option-name">{secret.name}</span>
                {secret.description && (
                  <span className="secret-option-description">{secret.description}</span>
                )}
              </div>
            </Select.Option>
          ))}
        </Select>

        <Tooltip title="Обновить список">
          <Button icon={<ReloadOutlined />} onClick={loadSecrets} disabled={disabled || loading} />
        </Tooltip>

        {allowReveal && selectedSecret && (
          <Tooltip title="Показать данные">
            <Button icon={<EyeOutlined />} onClick={handleReveal} disabled={disabled} />
          </Tooltip>
        )}

        {allowCreate && (
          <Tooltip title="Создать новый секрет">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              disabled={disabled}
            />
          </Tooltip>
        )}
      </Space.Compact>

      {selectedSecret && (
        <div className="secret-selector-info">
          <span className="secret-selector-info-label">Описание:</span>
          <span className="secret-selector-info-value">
            {selectedSecret.description || 'Нет описания'}
          </span>
          {selectedSecret.last_used_at && (
            <>
              <span className="secret-selector-info-label">Последнее использование:</span>
              <span className="secret-selector-info-value">
                {new Date(selectedSecret.last_used_at).toLocaleString('ru-RU')}
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default SecretSelector;
