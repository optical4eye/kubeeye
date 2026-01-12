import React from 'react';
import { CloseCircleOutlined } from '@ant-design/icons';

interface LoadingScreenProps {
  message?: string;
  subMessage?: string;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message = 'Система запускается',
  subMessage = 'Пожалуйста, подождите...',
}) => {
  const statusInfo = {
    status: 'error' as const,
    text: 'Недоступен',
    icon: <CloseCircleOutlined />,
    color: 'red',
  };
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🚀</div>
        <h1 style={{ color: 'white', margin: '0 0 0.5rem 0', fontSize: '2.5rem' }}>KubeEye</h1>
        <p style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '1.1rem', margin: '0 0 2rem 0' }}>
          Kubernetes Cluster Inspection Tool
        </p>
      </div>

      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width: '48px',
            height: '48px',
            border: '4px solid rgba(255, 255, 255, 0.3)',
            borderTop: '4px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 2rem auto',
          }}
        />
        <h2 style={{ color: 'white', margin: '0 0 1rem 0', fontSize: '1.5rem' }}>{message}</h2>
        <p style={{ color: 'rgba(255, 255, 255, 0.7)', margin: '0 0 2rem 0' }}>{subMessage}</p>
      </div>

      {/* Backend Status Section */}
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            marginBottom: '0.5rem',
          }}
        >
          {statusInfo.icon}
          <span style={{ color: 'white', fontSize: '1rem' }}>Backend: {statusInfo.text}</span>
        </div>
      </div>

      <div style={{ textAlign: 'center' }}>
        <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '0.9rem', margin: 0 }}>
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
