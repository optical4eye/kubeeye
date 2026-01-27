import { create } from 'zustand';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { MessageType, TaskMessage, InspectionMessage } from '../services/websocket/messageTypes';

export type WebSocketStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface WebSocketState {
  // Connection state
  status: WebSocketStatus;
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;
  reconnectAttempts: number;
  lastConnectionTime: Date | null;

  // Messages
  lastMessage: MessageType | null;
  messages: MessageType[];

  // Connection manager instance
  connectionManager: WebSocketConnectionManager | null;

  // Actions
  connect: (baseUrl: string, clientId?: string) => Promise<void>;
  disconnect: () => void;
  reconnect: () => Promise<void>;
  clearMessages: () => void;
  setConnectionError: (error: string | null) => void;
  resetError: () => void;

  // Subscription helpers
  subscribeToTasks: (handler: (message: TaskMessage) => void) => () => void;
  subscribeToInspections: (handler: (message: InspectionMessage) => void) => () => void;
  subscribeToAll: (handler: (message: MessageType) => void) => () => void;

  // Send messages
  sendMessage: (message: string) => void;
  sendJsonMessage: (message: any) => void;
}

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  status: 'disconnected',
  isConnected: false,
  isConnecting: false,
  connectionError: null,
  reconnectAttempts: 0,
  lastConnectionTime: null,
  lastMessage: null,
  messages: [],
  connectionManager: null,

  connect: async (baseUrl: string, clientId?: string) => {
    const { isConnecting, status } = get();

    if (isConnecting || status === 'connected') {
      return;
    }

    set({
      status: 'connecting',
      isConnecting: true,
      connectionError: null,
      reconnectAttempts: 0,
    });

    try {
      const manager = new WebSocketConnectionManager(baseUrl, clientId);

      // Set up message handling
      manager.subscribeToAll(message => {
        set(state => ({
          lastMessage: message,
          messages: [...state.messages.slice(-99), message], // Keep last 100 messages
        }));
      });

      // Set up error handling
      manager.onError(error => {
        console.error('WebSocket error:', error);
        set({
          status: 'error',
          connectionError: 'WebSocket connection error',
          isConnected: false,
          isConnecting: false,
        });
      });

      manager.onClose(event => {
        console.log('WebSocket closed:', event.code, event.reason);
        set({
          status: 'disconnected',
          isConnected: false,
          isConnecting: false,
        });
        if (event.code !== 1000) {
          // Not a clean disconnect
          set({
            status: 'error',
            connectionError: `Connection closed: ${event.reason || 'Unknown reason'}`,
          });
        }
      });

      await manager.connect();

      set({
        connectionManager: manager,
        status: 'connected',
        isConnected: true,
        isConnecting: false,
        connectionError: null,
        lastConnectionTime: new Date(),
        reconnectAttempts: 0,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to connect';
      set({
        status: 'error',
        isConnecting: false,
        connectionError: errorMessage,
        reconnectAttempts: get().reconnectAttempts + 1,
      });
      throw error;
    }
  },

  disconnect: () => {
    const { connectionManager } = get();
    if (connectionManager) {
      connectionManager.disconnect();
    }
    set({
      connectionManager: null,
      status: 'disconnected',
      isConnected: false,
      isConnecting: false,
      connectionError: null,
    });
  },

  reconnect: async () => {
    const { connectionManager } = get();
    if (connectionManager) {
      // Get the base URL from the connection manager or reconstruct it
      const baseUrl = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const fullBaseUrl = `${baseUrl}//${host}`;

      // Disconnect first
      get().disconnect();

      // Wait a bit before reconnecting
      setTimeout(() => {
        get().connect(fullBaseUrl);
      }, 1000);
    }
  },

  clearMessages: () => {
    set({ messages: [], lastMessage: null });
  },

  setConnectionError: (error: string | null) => {
    set({ connectionError: error });
  },

  resetError: () => {
    set({ connectionError: null, status: 'disconnected' });
  },

  subscribeToTasks: handler => {
    const { connectionManager } = get();
    if (connectionManager) {
      return connectionManager.subscribeToTasks(handler);
    }
    return () => {}; // No-op if not connected
  },

  subscribeToInspections: handler => {
    const { connectionManager } = get();
    if (connectionManager) {
      return connectionManager.subscribeToInspections(handler);
    }
    return () => {}; // No-op if not connected
  },

  subscribeToAll: handler => {
    const { connectionManager } = get();
    if (connectionManager) {
      return connectionManager.subscribeToAll(handler);
    }
    return () => {}; // No-op if not connected
  },

  sendMessage: message => {
    const { connectionManager } = get();
    if (connectionManager) {
      connectionManager.sendMessage(message);
    } else {
      // WebSocket not connected. Cannot send message.
    }
  },

  sendJsonMessage: message => {
    const { connectionManager } = get();
    if (connectionManager) {
      connectionManager.sendJsonMessage(message);
    } else {
      // WebSocket not connected. Cannot send message.
    }
  },
}));
