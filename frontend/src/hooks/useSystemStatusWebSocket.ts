import { useRef, useEffect, useState, useCallback } from 'react';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { SystemStatusMessage } from '../services/websocket/messageTypes';

interface SystemStatus {
  isReady: boolean;
  message?: string;
  subMessage?: string;
  isConnecting: boolean;
}

export const useSystemStatusWebSocket = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    isReady: false,
    message: undefined,
    subMessage: undefined,
    isConnecting: true,
  });
  const wsManagerRef = useRef<WebSocketConnectionManager | null>(null);

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
    });
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    // Get base URL from environment or window.location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseUrl = `${protocol}//${host}`;

    wsManagerRef.current = new WebSocketConnectionManager(baseUrl, '/ws/system-status');

    wsManagerRef.current
      .connect()
      .then(() => {
        // WebSocket connected for system status monitoring
        setSystemStatus(prev => ({ ...prev, isConnecting: false }));
      })
      .catch(() => {
        // WebSocket connection failed, fallback to connecting state
        setSystemStatus(prev => ({ ...prev, isConnecting: true }));
      });

    // Subscribe to system status messages
    const unsubscribe = wsManagerRef.current.subscribeToSystemStatus((message: SystemStatusMessage) => {
      handleSystemStatusMessage(message);
    });

    return () => {
      unsubscribe();
      wsManagerRef.current?.disconnect();
    };
  }, [handleSystemStatusMessage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsManagerRef.current?.disconnect();
    };
  }, []);

  return systemStatus;
};