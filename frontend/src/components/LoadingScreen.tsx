import React from 'react';
import { CloseCircleOutlined } from '@ant-design/icons';
import { theme } from 'antd';

interface LoadingScreenProps {
  message?: string;
  subMessage?: string;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message = 'Система запускается',
  subMessage = 'Пожалуйста, подождите...',
}) => {
  const { token } = theme.useToken();
  const statusInfo = {
    status: 'error' as const,
    text: 'Недоступен',
    icon: <CloseCircleOutlined />,
    color: '#ff4d4f',
  };
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #141414, #000000)',
        color: 'white',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', marginBottom: token.margin }}>🚀</div>
        <h1 style={{ color: 'white', margin: `0 0 ${token.margin} 0`, fontSize: '2.5rem' }}>
          KubeEye
        </h1>
        <p
          style={{
            color: '#a6a6a6',
            fontSize: '1.1rem',
            margin: `0 0 ${token.margin} 0`,
          }}
        >
          Kubernetes Cluster Inspection Tool
        </p>
      </div>

      <div style={{ textAlign: 'center', marginTop: token.marginXXL }}>
        <div
          style={{
            width: '48px',
            height: '48px',
            border: '4px solid #434343',
            borderTop: '4px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: `0 0 ${token.margin} 0`,
            position: 'relative',
            left: '50%',
            transform: 'translateX(-50%)',
          }}
        />
        <h2 style={{ color: 'white', margin: `0 0 ${token.marginSM} 0`, fontSize: '1.5rem' }}>
          {message}
        </h2>
        <p style={{ color: '#a6a6a6', margin: `0 0 ${token.margin} 0` }}>{subMessage}</p>
      </div>

      {/* Backend Status Section */}
      <div style={{ textAlign: 'center', marginTop: token.marginXXL, marginBottom: token.margin }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: token.marginSM,
            marginBottom: token.marginSM,
          }}
        >
          {statusInfo.icon}
          <span style={{ color: 'white', fontSize: '1rem' }}>Backend: {statusInfo.text}</span>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: token.margin }}>
        <p style={{ color: '#a6a6a6', fontSize: '0.9rem', margin: 0 }}>
          Подготовка системы к работе...
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
