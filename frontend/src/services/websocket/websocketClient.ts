// WebSocket client for connecting to backend WebSocket endpoint

import { WebSocketMessage, MessageType } from './messageTypes';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId?: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000; // ms
  private isConnecting = false;
  private messageHandlers: ((message: MessageType) => void)[] = [];
  private errorHandlers: ((error: Event) => void)[] = [];
  private closeHandlers: ((event: CloseEvent) => void)[] = [];

  constructor(url: string, clientId?: string) {
    this.url = url;
    this.clientId = clientId;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
        resolve();
        return;
      }

      this.isConnecting = true;
      const fullUrl = this.clientId ? `${this.url}?client_id=${this.clientId}` : this.url;

      try {
        this.ws = new WebSocket(fullUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = event => {
          try {
            const message: MessageType = JSON.parse(event.data);
            this.messageHandlers.forEach(handler => handler(message));
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onerror = error => {
          console.error('WebSocket error:', error);
          this.errorHandlers.forEach(handler => handler(error));
          this.isConnecting = false;
          reject(error);
        };

        this.ws.onclose = event => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.closeHandlers.forEach(handler => handler(event));
          this.isConnecting = false;

          // Attempt to reconnect if not intentionally closed
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++;
    console.log(
      `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
    );

    setTimeout(() => {
      this.connect().catch(() => {
        // Reconnect failed, will try again if attempts remain
      });
    }, this.reconnectInterval * this.reconnectAttempts);
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent further reconnects
  }

  send(message: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      console.warn('WebSocket is not connected. Cannot send message.');
    }
  }

  sendJson(message: WebSocketMessage): void {
    this.send(JSON.stringify(message));
  }

  onMessage(handler: (message: MessageType) => void): void {
    this.messageHandlers.push(handler);
  }

  offMessage(handler: (message: MessageType) => void): void {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  onError(handler: (error: Event) => void): void {
    this.errorHandlers.push(handler);
  }

  onClose(handler: (event: CloseEvent) => void): void {
    this.closeHandlers.push(handler);
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getReadyState(): number | undefined {
    return this.ws?.readyState;
  }
}
