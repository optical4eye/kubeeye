// WebSocket message types for frontend client

export interface WebSocketMessage {
  type: string;
  payload: Record<string, any>;
  timestamp: string; // ISO string
  target?: string[];
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

export interface SystemStatusMessage extends WebSocketMessage {
  type: 'system_status';
  payload: {
    status: 'healthy' | 'unhealthy';
    timestamp: string;
    queue: {
      running: boolean;
      active_workers: number;
      pending_tasks: number;
    };
    clusters_count?: number;
    version: string;
  };
}

export type MessageType = TaskMessage | InspectionMessage | SystemStatusMessage | PingMessage | PongMessage | WebSocketMessage;

// Echo message for responses
export interface EchoMessage extends WebSocketMessage {
  type: 'echo';
  payload: {
    message: string;
  };
}

// Ping message for keep-alive
export interface PingMessage extends WebSocketMessage {
  type: 'ping';
  payload: Record<string, any>; // Can be empty or contain timestamp
}

// Pong message for keep-alive response
export interface PongMessage extends WebSocketMessage {
  type: 'pong';
  payload: Record<string, any>; // Can be empty or contain timestamp
}
