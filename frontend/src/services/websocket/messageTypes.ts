// WebSocket message types for frontend client

export interface WebSocketMessage {
  type: string;
  payload: Record<string, any>;
  timestamp: string; // ISO string
}

export interface TaskMessage extends WebSocketMessage {
  type: 'task_scheduled' | 'task_started' | 'task_completed' | 'task_failed';
  payload: {
    task_id: string;
    task_type?: string;
    result?: any;
    error?: string;
  };
}

export interface InspectionMessage extends WebSocketMessage {
  type: 'inspection_started' | 'inspection_completed' | 'inspection_failed';
  payload: {
    cluster_name: string;
    config?: Record<string, any>;
    result?: Record<string, any>;
    error?: string;
  };
}

export type MessageType = TaskMessage | InspectionMessage | WebSocketMessage;

// Echo message for responses
export interface EchoMessage extends WebSocketMessage {
  type: 'echo';
  payload: {
    message: string;
  };
}
