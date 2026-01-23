import React from 'react';
import { CloseCircleOutlined } from '@ant-design/icons';
import { theme } from 'antd';
import { useTranslation } from 'react-i18next';

interface LoadingScreenProps {
  message?: string;
  subMessage?: string;
  isConnecting?: boolean;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({ message, subMessage, isConnecting = false }) => {
  const { t } = useTranslation();
  const { token } = theme.useToken();
  const statusInfo = isConnecting
    ? {
        status: 'processing' as const,
        text: t('loadingScreen.connecting'),
        icon: <div style={{ width: '16px', height: '16px', border: '2px solid #1890ff', borderTop: '2px solid transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />,
        color: '#1890ff',
      }
    : {
        status: 'error' as const,
        text: t('loadingScreen.unavailable'),
        icon: <CloseCircleOutlined />,
        color: '#ff4d4f',
      };

  const defaultMessage = t('loadingScreen.systemStarting');
  const defaultSubMessage = t('loadingScreen.pleaseWait');
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '2rem',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #141414, #000000)',
        color: 'white',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', margin: '0.5rem 0' }}>🚀</div>
        <h1 style={{ color: 'white', margin: '0.5rem 0', fontSize: '2.5rem' }}>KubeEye</h1>
        <p
          style={{
            color: '#a6a6a6',
            fontSize: '1.1rem',
            margin: '0.5rem 0',
          }}
        >
          {t('header.title')}
        </p>
      </div>

      <div style={{ textAlign: 'center' }}>
        <h2 style={{ color: 'white', margin: '0.5rem 0', fontSize: '1.5rem' }}>
          {message || defaultMessage}
        </h2>
        <p style={{ color: '#a6a6a6', margin: '0.5rem 0' }}>{subMessage || defaultSubMessage}</p>
      </div>

      <div style={{ textAlign: 'center' }}>
        {/* Backend Status Section */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: token.marginSM,
            margin: '0.5rem 0',
          }}
        >
          {statusInfo.icon}
          <span style={{ color: 'white', fontSize: '1rem' }}>
            {t('loadingScreen.backend')}: {statusInfo.text}
          </span>
        </div>
        <p style={{ color: '#a6a6a6', fontSize: '0.9rem', margin: '0.5rem 0' }}>
          {t('loadingScreen.preparingSystem')}
        </p>
      </div>

      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );
};

export default LoadingScreen;
