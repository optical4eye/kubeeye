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
    const wsUrl = `${baseUrl}/ws/system-status`;

    console.log('WebSocket: Attempting to connect to:', wsUrl);

    wsManagerRef.current = new WebSocketConnectionManager(baseUrl, '/ws/system-status');

    wsManagerRef.current
      .connect()
      .then(() => {
        console.log('WebSocket: Connected successfully to system status');
        // WebSocket connected for system status monitoring
        setSystemStatus(prev => ({ ...prev, isConnecting: false }));
      })
      .catch((error) => {
        console.error('WebSocket: Connection failed:', error);
        // WebSocket connection failed, fallback to connecting state
        setSystemStatus(prev => ({ ...prev, isConnecting: true }));
      });

    // Add error and close handlers for logging
    wsManagerRef.current.onError((error) => {
      console.error('WebSocket: Error event:', error);
    });

    wsManagerRef.current.onClose((event) => {
      console.log('WebSocket: Closed with code:', event.code, 'reason:', event.reason);
    });

    // Subscribe to system status messages
    const unsubscribe = wsManagerRef.current.subscribeToSystemStatus(
      (message: SystemStatusMessage) => {
        handleSystemStatusMessage(message);
      }
    );

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
