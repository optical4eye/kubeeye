import React from 'react';
import { CloseCircleOutlined } from '@ant-design/icons';
import { theme } from 'antd';
import { useTranslation } from 'react-i18next';
import { useUIStore } from '../../stores/uiStore';

interface LoadingScreenProps {
  message?: string;
  subMessage?: string;
  isConnecting?: boolean;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message,
  subMessage,
  isConnecting = false,
}) => {
  const { t } = useTranslation();
  const { token } = theme.useToken();
  const { theme: uiTheme } = useUIStore();
  const statusInfo = isConnecting
    ? {
        status: 'processing' as const,
        text: t('loadingScreen.connecting'),
        icon: <div className="loading-spinner-icon" />,
        color: token.colorPrimary,
      }
    : {
        status: 'error' as const,
        text: t('loadingScreen.unavailable'),
        icon: <CloseCircleOutlined />,
        color: token.colorError,
      };

  const defaultMessage = t('loadingScreen.systemStarting');
  const defaultSubMessage = t('loadingScreen.pleaseWait');
  return (
    <div
      className={`loading-screen ${uiTheme === 'dark' ? 'loading-screen-dark' : 'loading-screen-light'}`}
    >
      <div className="loading-screen-content">
        <div className="loading-screen-emoji">🚀</div>
        <h1 className="loading-screen-title">KubeEye</h1>
        <p
          className={`loading-screen-subtitle ${uiTheme === 'dark' ? 'loading-screen-subtitle-dark' : 'loading-screen-subtitle-light'}`}
        >
          {t('header.title')}
        </p>
      </div>

      <div className="loading-screen-status">
        <h2
          className={`loading-screen-status-title ${uiTheme === 'dark' ? 'loading-screen-subtitle-dark' : 'loading-screen-subtitle-light'}`}
        >
          {message || defaultMessage}
        </h2>
        <p
          className={`loading-screen-subtitle ${uiTheme === 'dark' ? 'loading-screen-subtitle-dark' : 'loading-screen-subtitle-light'}`}
        >
          {subMessage || defaultSubMessage}
        </p>
      </div>

      <div className="loading-screen-status">
        {/* Backend Status Section */}
        <div className="kube-display-flex kube-align-center kube-justify-center kube-margin-8">
          {statusInfo.icon}
          <span
            className={`loading-screen-status-text ${uiTheme === 'dark' ? 'loading-screen-subtitle-dark' : 'loading-screen-subtitle-light'}`}
          >
            {t('loadingScreen.backend')}: {statusInfo.text}
          </span>
        </div>
        <p
          className={`loading-screen-subtitle ${uiTheme === 'dark' ? 'loading-screen-subtitle-dark' : 'loading-screen-subtitle-light'} kube-font-size-14px kube-margin-8`}
        >
          {t('loadingScreen.preparingSystem')}
        </p>
      </div>
    </div>
  );
};

export default LoadingScreen;
