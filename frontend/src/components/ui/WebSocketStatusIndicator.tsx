import React from 'react';
import { Badge, Tooltip, Button } from 'antd';
import { WifiOutlined, LoadingOutlined, ExclamationCircleOutlined, DisconnectOutlined } from '@ant-design/icons';
import { useWebSocketStore, WebSocketStatus } from '../../stores/websocketStore';
import { useTranslation } from 'react-i18next';

const WebSocketStatusIndicator: React.FC = () => {
  const { t } = useTranslation();
  const { status, connectionError, reconnectAttempts, reconnect } = useWebSocketStore();

  const getStatusConfig = (status: WebSocketStatus) => {
    switch (status) {
      case 'connected':
        return {
          color: 'green',
          icon: <WifiOutlined />,
          text: t('websocket.connected', 'Connected'),
          tooltip: t('websocket.connectedTooltip', 'WebSocket connection is active'),
        };
      case 'connecting':
        return {
          color: 'blue',
          icon: <LoadingOutlined spin />,
          text: t('websocket.connecting', 'Connecting'),
          tooltip: t('websocket.connectingTooltip', 'Establishing WebSocket connection...'),
        };
      case 'disconnected':
        return {
          color: 'orange',
          icon: <DisconnectOutlined />,
          text: t('websocket.disconnected', 'Disconnected'),
          tooltip: t('websocket.disconnectedTooltip', 'WebSocket connection lost'),
        };
      case 'error':
        return {
          color: 'red',
          icon: <ExclamationCircleOutlined />,
          text: t('websocket.error', 'Connection Error'),
          tooltip: connectionError || t('websocket.errorTooltip', 'WebSocket connection failed'),
        };
      default:
        return {
          color: 'gray',
          icon: <DisconnectOutlined />,
          text: t('websocket.unknown', 'Unknown'),
          tooltip: t('websocket.unknownTooltip', 'Connection status unknown'),
        };
    }
  };

  const config = getStatusConfig(status);

  const handleReconnect = () => {
    reconnect();
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <Tooltip title={config.tooltip}>
        <Badge
          color={config.color}
          text={
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {config.icon}
              {config.text}
              {reconnectAttempts > 0 && (
                <span style={{ fontSize: '12px', color: '#999' }}>
                  ({reconnectAttempts})
                </span>
              )}
            </span>
          }
        />
      </Tooltip>

      {(status === 'error' || status === 'disconnected') && (
        <Button
          size="small"
          type="link"
          onClick={handleReconnect}
          loading={status === 'connecting'}
        >
          {t('websocket.reconnect', 'Reconnect')}
        </Button>
      )}
    </div>
  );
};

export default WebSocketStatusIndicator;