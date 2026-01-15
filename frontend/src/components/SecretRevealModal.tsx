/**
 * SecretRevealModal component for securely displaying decrypted secret data
 * Features:
 * - Auto-hide after 30 seconds
 * - Copy to clipboard
 * - Security warning
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Modal, Button, Space, message, Alert, Typography, Spin, Divider } from 'antd';
import { CopyOutlined, EyeInvisibleOutlined, LockOutlined } from '@ant-design/icons';
import { Secret, SecretReveal } from '../types/secret';
import { secretApi } from '../services/secretApi';
import '../styles/SecretRevealModal.css';

const { Text, Paragraph } = Typography;

interface SecretRevealModalProps {
  secret: Secret;
  open: boolean;
  onClose: () => void;
}

const SecretRevealModal: React.FC<SecretRevealModalProps> = ({ secret, open, onClose }) => {
  const [revealedData, setRevealedData] = useState<SecretReveal | null>(null);
  const [loading, setLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(30);
  const [isCopied, setIsCopied] = useState(false);

  const loadRevealedData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await secretApi.revealSecret(secret.id);
      setRevealedData(data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || 'Не удалось расшифровать данные');
      onClose();
    } finally {
      setLoading(false);
    }
  }, [secret.id, onClose]);

  useEffect(() => {
    if (open) {
      loadRevealedData();
      setTimeLeft(30);
    } else {
      setRevealedData(null);
      setIsCopied(false);
    }
  }, [open, loadRevealedData]);

  useEffect(() => {
    let countdown: ReturnType<typeof setInterval> | null = null;

    if (open && timeLeft > 0) {
      countdown = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && open) {
      message.warning('Данные будут скрыты для безопасности');
      onClose();
    }

    return () => {
      if (countdown) {
        clearInterval(countdown);
      }
    };
  }, [open, timeLeft, onClose]);

  const handleCopy = async () => {
    if (revealedData) {
      try {
        await navigator.clipboard.writeText(revealedData.data);
        setIsCopied(true);
        message.success('Скопировано в буфер обмена');
        setTimeout(() => setIsCopied(false), 2000);
      } catch {
        message.error('Не удалось скопировать');
      }
    }
  };

  const getTypeLabel = (type: string): string => {
    switch (type) {
      case 'password':
        return 'Пароль';
      case 'ssh_key':
        return 'SSH ключ';
      case 'kubeconfig':
        return 'Kubeconfig';
      default:
        return type;
    }
  };

  const formatData = (data: string, type: string): string => {
    if (type === 'kubeconfig' || type === 'ssh_key') {
      return data;
    }
    return data;
  };

  return (
    <Modal
      title={`Просмотр: ${secret.name}`}
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="close" icon={<EyeInvisibleOutlined />} onClick={onClose}>
          Скрыть ({timeLeft} сек)
        </Button>,
      ]}
      width={800}
      className="secret-reveal-modal"
    >
      <Alert
        message={
          <Space>
            <LockOutlined />
            <Text>Данные будут автоматически скрыты через {timeLeft} секунд для безопасности</Text>
          </Space>
        }
        type="warning"
        showIcon
        className="secret-reveal-warning"
      />

      {loading ? (
        <div className="secret-reveal-loading">
          <Spin size="large" />
          <Text>Расшифровка данных...</Text>
        </div>
      ) : revealedData ? (
        <div className="secret-reveal-content">
          <div className="secret-reveal-info">
            <Space direction="vertical" size="small">
              <div>
                <Text strong>Тип:</Text> {getTypeLabel(revealedData.secret_type)}
              </div>
              <div>
                <Text strong>Название:</Text> {revealedData.name}
              </div>
              {revealedData.description && (
                <div>
                  <Text strong>Описание:</Text> {revealedData.description}
                </div>
              )}
            </Space>
          </div>

          <Divider />

          <div className="secret-reveal-data">
            <div className="secret-reveal-data-header">
              <Text strong>Данные:</Text>
              <Button type="primary" size="small" icon={<CopyOutlined />} onClick={handleCopy}>
                {isCopied ? 'Скопировано' : 'Копировать'}
              </Button>
            </div>
            <Paragraph code className="secret-reveal-data-text">
              {formatData(revealedData.data, revealedData.secret_type)}
            </Paragraph>
          </div>
        </div>
      ) : null}
    </Modal>
  );
};

export default SecretRevealModal;
