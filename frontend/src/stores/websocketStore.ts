import { create } from 'zustand';
import { WebSocketConnectionManager } from '../services/websocket/connectionManager';
import { MessageType, TaskMessage, InspectionMessage } from '../services/websocket/messageTypes';

interface WebSocketState {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  // Messages
  lastMessage: MessageType | null;
  messages: MessageType[];

  // Connection manager instance
  connectionManager: WebSocketConnectionManager | null;

  // Actions
  connect: (baseUrl: string, clientId?: string) => Promise<void>;
  disconnect: () => void;
  clearMessages: () => void;
  setConnectionError: (error: string | null) => void;

  // Subscription helpers
  subscribeToTasks: (handler: (message: TaskMessage) => void) => () => void;
  subscribeToInspections: (handler: (message: InspectionMessage) => void) => () => void;
  subscribeToAll: (handler: (message: MessageType) => void) => () => void;

  // Send messages
  sendMessage: (message: string) => void;
  sendJsonMessage: (message: any) => void;
}

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  isConnected: false,
  isConnecting: false,
  connectionError: null,
  lastMessage: null,
  messages: [],
  connectionManager: null,

  connect: async (baseUrl: string, clientId?: string) => {
    const { connectionManager, isConnecting } = get();

    if (isConnecting || (connectionManager && connectionManager.isConnected())) {
      return;
    }

    set({ isConnecting: true, connectionError: null });

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
      manager.onError(_error => {
        set({ connectionError: 'WebSocket connection error' });
      });

      manager.onClose(event => {
        set({ isConnected: false, isConnecting: false });
        if (event.code !== 1000) {
          // Not a clean disconnect
          set({ connectionError: `Connection closed: ${event.reason || 'Unknown reason'}` });
        }
      });

      await manager.connect();

      set({
        connectionManager: manager,
        isConnected: true,
        isConnecting: false,
        connectionError: null,
      });
    } catch (error) {
      set({
        isConnecting: false,
        connectionError: error instanceof Error ? error.message : 'Failed to connect',
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
      isConnected: false,
      isConnecting: false,
      connectionError: null,
    });
  },

  clearMessages: () => {
    set({ messages: [], lastMessage: null });
  },

  setConnectionError: error => {
    set({ connectionError: error });
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
