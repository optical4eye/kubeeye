export interface WebSocketMessage {
  type: string;
  payload: { [key: string]: string };
  timestamp: string;
  target: string[];
}

export interface TaskScheduledMessage {
  taskId: string;
  taskType: string;
}

export interface TaskStartedMessage {
  taskId: string;
  taskType: string;
}

export interface TaskCompletedMessage {
  taskId: string;
  result: string;
}

export interface TaskFailedMessage {
  taskId: string;
  error: string;
}

export interface InspectionStartedMessage {
  clusterName: string;
  config: string;
}

export interface InspectionCompletedMessage {
  clusterName: string;
  result: string;
}

export interface InspectionFailedMessage {
  clusterName: string;
  error: string;
}

export interface QueueStatus {
  running: boolean;
  activeWorkers: number;
  pendingTasks: number;
}

export interface SystemStatusMessage {
  status: string;
  queue?: QueueStatus;
  clustersCount: number;
  version: string;
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface PingMessage {}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface PongMessage {}

export interface EchoMessage {
  message: string;
}

export interface WebSocketMessageUnion {
  taskScheduled?: TaskScheduledMessage;
  taskStarted?: TaskStartedMessage;
  taskCompleted?: TaskCompletedMessage;
  taskFailed?: TaskFailedMessage;
  inspectionStarted?: InspectionStartedMessage;
  inspectionCompleted?: InspectionCompletedMessage;
  inspectionFailed?: InspectionFailedMessage;
  systemStatus?: SystemStatusMessage;
  ping?: PingMessage;
  pong?: PongMessage;
  echo?: EchoMessage;
  timestamp: string;
  target: string[];
}
