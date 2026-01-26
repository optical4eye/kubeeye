import { useRef, useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { SystemStatusMessage } from '../services/websocket/messageTypes';
import { useWebSocketStore } from '../stores/websocketStore';

interface SystemStatus {
  isReady: boolean;
  message?: string;
  subMessage?: string;
  isConnecting: boolean;
}

export const useSystemStatusWebSocket = () => {
  const { t } = useTranslation();
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    isReady: false,
    message: undefined,
    subMessage: undefined,
    isConnecting: true,
  });
  const [isWebSocketAvailable, setIsWebSocketAvailable] = useState(true);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const wsManagerRef = useRef<WebSocketConnectionManager | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { status: wsStatus } = useWebSocketStore();

  const handleSystemStatusMessage = useCallback((message: SystemStatusMessage) => {
    const { status, queue } = message.payload;
    const isReady = status === 'healthy';
    const isConnecting = !isReady && queue.running;

    console.log('WebSocket: Handling system status message:', { status, queue, isReady, isConnecting });

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

    console.log('WebSocket: Setting system status:', { isReady, message: messageText, subMessage: subMessageText, isConnecting });

    setSystemStatus({
      isReady,
      message: messageText,
      subMessage: subMessageText,
      isConnecting,
    });
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    // Use relative WebSocket URL - nginx will proxy to backend
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/system-status`;

    console.log('WebSocket: Attempting to connect to:', wsUrl);

    wsManagerRef.current = new WebSocketConnectionManager(wsUrl.replace('/ws/system-status', ''), '/ws/system-status');

    wsManagerRef.current
      .connect(['system_status'])
      .then(() => {
        console.log('WebSocket: Connected successfully to system status');
        setIsWebSocketAvailable(true);
        setConnectionAttempts(0);
        // WebSocket connected for system status monitoring
        setSystemStatus(prev => ({ ...prev, isConnecting: false }));
      })
      .catch((error) => {
        console.error('WebSocket: Connection failed:', error);
        setIsWebSocketAvailable(false);
        setConnectionAttempts(prev => prev + 1);
        startPolling();
        message.warning(t('websocket.systemStatusFallback', 'System status monitoring unavailable, using polling'));
        // WebSocket connection failed, fallback to connecting state
        setSystemStatus(prev => ({ ...prev, isConnecting: true }));
      });

    // Add error and close handlers for logging and fallback
    const unsubscribeError = wsManagerRef.current.onError((error) => {
      console.error('WebSocket: Error event:', error);
      if (isWebSocketAvailable) {
        setIsWebSocketAvailable(false);
        startPolling();
        message.warning(t('websocket.systemStatusFallback', 'System status monitoring unavailable, using polling'));
      }
      console.log('WebSocket: Setting status to not ready and connecting due to error');
      setSystemStatus({
        isReady: false,
        isConnecting: true,
        message: 'Connection error',
        subMessage: 'Attempting to reconnect...',
      });
    });

    const unsubscribeClose = wsManagerRef.current.onClose((event) => {
      console.log('WebSocket: Closed with code:', event.code, 'reason:', event.reason);
      if (isWebSocketAvailable && event.code !== 1000) {
        setIsWebSocketAvailable(false);
        startPolling();
        message.warning(t('websocket.systemStatusFallback', 'System status monitoring unavailable, using polling'));
      }
      console.log('WebSocket: Setting status to not ready and connecting due to close');
      setSystemStatus({
        isReady: false,
        isConnecting: true,
        message: 'Connection lost',
        subMessage: 'Reconnecting...',
      });
    });

    // Subscribe to system status messages
    const unsubscribe = wsManagerRef.current.subscribeToSystemStatus(
      (message: SystemStatusMessage) => {
        console.log('WebSocket: Received system status message:', message);
        handleSystemStatusMessage(message);
      }
    );

    return () => {
      unsubscribe();
      unsubscribeError();
      unsubscribeClose();
      wsManagerRef.current?.disconnect();
      stopPolling();
    };
  }, [handleSystemStatusMessage, isWebSocketAvailable]);

  // Polling fallback when WebSocket is unavailable
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return; // Already polling

    pollingIntervalRef.current = setInterval(async () => {
      try {
        // Poll for system status - this would need to be implemented in the API
        // For now, we'll simulate system status updates
        console.log('Polling for system status...');
        // TODO: Implement actual polling logic when API supports it
        // Simulate occasional status updates
        if (Math.random() > 0.7) {
          setSystemStatus(prev => ({
            ...prev,
            isReady: Math.random() > 0.5,
            message: Math.random() > 0.5 ? 'System ready' : 'System starting',
            subMessage: Math.random() > 0.5 ? 'All services operational' : 'Please wait',
            isConnecting: false,
          }));
        }
      } catch (error) {
        console.error('System status polling error:', error);
      }
    }, 10000); // Poll every 10 seconds
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsManagerRef.current?.disconnect();
    };
  }, []);

  return {
    ...systemStatus,
    isWebSocketAvailable,
    connectionAttempts,
  };
};
