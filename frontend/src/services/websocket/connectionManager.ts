// WebSocket connection manager for managing subscriptions and message handling

import { WebSocketClient } from './websocketClient';
import { MessageType, TaskMessage, InspectionMessage } from './messageTypes';

export type MessageHandler<T extends MessageType> = (message: T) => void;

export class WebSocketConnectionManager {
  private client: WebSocketClient;
  private taskHandlers: MessageHandler<TaskMessage>[] = [];
  private inspectionHandlers: MessageHandler<InspectionMessage>[] = [];
  private generalHandlers: MessageHandler<MessageType>[] = [];

  constructor(baseUrl: string, clientId?: string) {
    // Assuming the WebSocket endpoint is at /ws/tasks
    const wsUrl = `ws://${baseUrl}/ws/tasks`;
    this.client = new WebSocketClient(wsUrl, clientId);

    // Set up message routing
    this.client.onMessage(message => {
      this.routeMessage(message);
    });
  }

  async connect(): Promise<void> {
    await this.client.connect();
  }

  disconnect(): void {
    this.client.disconnect();
  }

  isConnected(): boolean {
    return this.client.isConnected();
  }

  private routeMessage(message: MessageType): void {
    // Call general handlers
    this.generalHandlers.forEach(handler => handler(message));

    // Route to specific handlers based on type
    if (this.isTaskMessage(message)) {
      this.taskHandlers.forEach(handler => handler(message));
    } else if (this.isInspectionMessage(message)) {
      this.inspectionHandlers.forEach(handler => handler(message));
    }
  }

  private isTaskMessage(message: MessageType): message is TaskMessage {
    return ['task_scheduled', 'task_started', 'task_completed', 'task_failed'].includes(
      message.type
    );
  }

  private isInspectionMessage(message: MessageType): message is InspectionMessage {
    return ['inspection_started', 'inspection_completed', 'inspection_failed'].includes(
      message.type
    );
  }

  // Subscription methods
  subscribeToTasks(handler: MessageHandler<TaskMessage>): () => void {
    this.taskHandlers.push(handler);
    return () => this.unsubscribeFromTasks(handler);
  }

  unsubscribeFromTasks(handler: MessageHandler<TaskMessage>): void {
    this.taskHandlers = this.taskHandlers.filter(h => h !== handler);
  }

  subscribeToInspections(handler: MessageHandler<InspectionMessage>): () => void {
    this.inspectionHandlers.push(handler);
    return () => this.unsubscribeFromInspections(handler);
  }

  unsubscribeFromInspections(handler: MessageHandler<InspectionMessage>): void {
    this.inspectionHandlers = this.inspectionHandlers.filter(h => h !== handler);
  }

  subscribeToAll(handler: MessageHandler<MessageType>): () => void {
    this.generalHandlers.push(handler);
    return () => this.unsubscribeFromAll(handler);
  }

  unsubscribeFromAll(handler: MessageHandler<MessageType>): void {
    this.generalHandlers = this.generalHandlers.filter(h => h !== handler);
  }

  // Send messages to server
  sendMessage(message: string): void {
    this.client.send(message);
  }

  sendJsonMessage(message: any): void {
    this.client.sendJson(message);
  }

  // Event handlers
  onError(handler: (error: Event) => void): void {
    this.client.onError(handler);
  }

  onClose(handler: (event: CloseEvent) => void): void {
    this.client.onClose(handler);
  }
}
