import { useRef, useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { SystemStatusMessage } from '../services/websocket/messageTypes';

interface SystemStatus {
  isReady: boolean;
  message?: string;
  subMessage?: string;
  isConnecting: boolean;
  wsStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  wsError?: string;
}

export const useSystemStatusWebSocket = () => {
  const { t } = useTranslation();
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    isReady: false,
    message: undefined,
    subMessage: undefined,
    isConnecting: true,
    wsStatus: 'connecting',
    wsError: undefined,
  });
  const [isWebSocketAvailable, setIsWebSocketAvailable] = useState(true);
  const [isTabVisible, setIsTabVisible] = useState(!document.hidden);
  const wsManagerRef = useRef<WebSocketConnectionManager | null>(null);
  const isWarningShownRef = useRef(false);

  const handleSystemStatusMessage = useCallback((message: SystemStatusMessage) => {
    const { status, queue } = message.payload;
    const isReady = status === 'healthy';
    const isConnecting = !isReady && queue.running;

    let messageText: string | undefined;
    let subMessageText: string | undefined;

    if (isReady) {
      messageText = 'System ready';
      subMessageText = 'All services operational';
    } else if (isConnecting) {
      messageText = 'System starting';
      subMessageText = 'Please wait';
    } else {
      messageText = 'System unavailable';
      subMessageText = 'Checking system status';
    }

    setSystemStatus({
      isReady,
      message: messageText,
      subMessage: subMessageText,
      isConnecting,
      wsStatus: 'connected', // WebSocket is connected since we received a message
      wsError: undefined,
    });
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    // Use relative WebSocket URL - nginx will proxy to backend
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    wsManagerRef.current = new WebSocketConnectionManager(wsUrl);

    if (isTabVisible) {
      wsManagerRef.current
        .connect(['system_status'])
        .then(() => {
          setIsWebSocketAvailable(true);
          isWarningShownRef.current = false;
          // WebSocket connected for system status monitoring
          setSystemStatus(prev => ({
            ...prev,
            isConnecting: false,
            wsStatus: 'connected',
            wsError: undefined,
          }));
        })
        .catch(error => {
          console.error('WebSocket: Connection failed:', error);
          setIsWebSocketAvailable(false);
          if (!document.hidden) {
            message.warning(
              t('websocket.systemStatusUnavailable', 'System status monitoring unavailable')
            );
          }
          // WebSocket connection failed, set to not ready
          setSystemStatus({
            isReady: false,
            isConnecting: false,
            message: 'Connection failed',
            subMessage: 'Unable to connect to system status',
            wsStatus: 'error',
            wsError: error.message || 'Connection failed',
          });
        });
    }

    // Add error and close handlers for logging and fallback
    const unsubscribeError = wsManagerRef.current.onError(error => {
      console.error('WebSocket: Error event:', error);
      if (isWebSocketAvailable && !isWarningShownRef.current && !document.hidden) {
        message.warning(
          t(
            'websocket.systemStatusFallback',
            'System status monitoring unavailable, attempting to reconnect'
          )
        );
        isWarningShownRef.current = true;
      }
      setSystemStatus(prev => ({
        ...prev,
        isReady: false,
        isConnecting: true,
        message: 'Connection error',
        subMessage: 'Attempting to reconnect...',
        wsStatus: 'error',
        wsError: error.message || 'Connection error',
      }));
    });

    const unsubscribeClose = wsManagerRef.current.onClose(event => {
      if (
        isWebSocketAvailable &&
        event.code !== 1000 &&
        !isWarningShownRef.current &&
        !document.hidden
      ) {
        message.warning(
          t(
            'websocket.systemStatusFallback',
            'System status monitoring unavailable, attempting to reconnect'
          )
        );
        isWarningShownRef.current = true;
      }
      setSystemStatus(prev => ({
        ...prev,
        isReady: false,
        isConnecting: true,
        message: 'Connection lost',
        subMessage: 'Reconnecting...',
        wsStatus: 'disconnected',
        wsError: `Connection closed: ${event.reason || 'Unknown reason'}`,
      }));
    });

    const unsubscribeReconnectFailed = wsManagerRef.current.onReconnectFailed(() => {
      if (isWebSocketAvailable) {
        setIsWebSocketAvailable(false);
        if (!document.hidden) {
          message.warning(
            t('websocket.systemStatusUnavailable', 'System status monitoring unavailable')
          );
        }
        setSystemStatus(prev => ({
          ...prev,
          isReady: false,
          isConnecting: false,
          message: 'Reconnection failed',
          subMessage: 'Unable to restore connection',
          wsStatus: 'error',
          wsError: 'Reconnection failed',
        }));
      }
    });

    const unsubscribeReconnectSuccess = wsManagerRef.current.onReconnectSuccess(() => {
      isWarningShownRef.current = false;
      window.location.reload();
    });

    // Subscribe to system status messages
    const unsubscribe = wsManagerRef.current.subscribeToSystemStatus(
      (message: SystemStatusMessage) => {
        handleSystemStatusMessage(message);
      }
    );

    // Handle visibility change - disconnect when tab is hidden
    const handleVisibilityChange = () => {
      const visible = !document.hidden;
      setIsTabVisible(visible);
      if (!visible) {
        wsManagerRef.current?.disconnect();
      } else {
        // Reconnect when tab becomes visible
        wsManagerRef.current?.connect(['system_status']).catch(error => {
          console.error('System status WebSocket reconnection failed:', error);
        });
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      unsubscribe();
      unsubscribeError();
      unsubscribeClose();
      unsubscribeReconnectFailed();
      unsubscribeReconnectSuccess();
      wsManagerRef.current?.disconnect();
    };
  }, [handleSystemStatusMessage, isWebSocketAvailable]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsManagerRef.current?.disconnect();
    };
  }, []);

  return {
    ...systemStatus,
    isWebSocketAvailable,
  };
};
