// WebSocket client for connecting to backend WebSocket endpoint

import { WebSocketMessage, MessageType, PongMessage } from './messageTypes';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId?: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 50; // Increased for more persistent reconnection
  private baseDelay = 1000; // Base delay for exponential backoff in ms
  private maxDelay = 30000; // Maximum delay for exponential backoff in ms
  private jitterMax = 1000; // Maximum jitter to prevent thundering herd in ms
  private isConnecting = false;
  private messageHandlers: ((message: MessageType) => void)[] = [];
  private errorHandlers: ((error: Event) => void)[] = [];
  private closeHandlers: ((event: CloseEvent) => void)[] = [];
  private reconnectFailedHandlers: (() => void)[] = [];
  private reconnectSuccessHandlers: (() => void)[] = [];

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
      const fullUrl = this.clientId ? `${this.url}${this.clientId}` : this.url;

      try {
        this.ws = new WebSocket(fullUrl);

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0; // Reset attempts on successful connection
          // Backend handles heartbeat, no need to start ping-pong from frontend
          resolve();
        };

        this.ws.onmessage = event => {
          try {
            const message: MessageType = JSON.parse(event.data);
            if (message.type === 'ping') {
              // Respond with pong to backend ping
              const pongMessage: PongMessage = {
                type: 'pong',
                payload: {},
                timestamp: new Date().toISOString(),
              };
              this.sendJson(pongMessage);
            }
            this.messageHandlers.forEach(handler => handler(message));
          } catch {
            // Failed to parse WebSocket message
          }
        };

        this.ws.onerror = error => {
          this.errorHandlers.forEach(handler => handler(error));
          this.isConnecting = false;
          reject(error);
        };

        this.ws.onclose = event => {
          this.closeHandlers.forEach(handler => handler(event));
          this.isConnecting = false;

          // Attempt to reconnect if not intentionally closed
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          } else {
            this.reconnectFailedHandlers.forEach(handler => handler());
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

    // Exponential backoff with jitter
    const exponentialDelay = Math.min(this.baseDelay * Math.pow(2, this.reconnectAttempts - 1), this.maxDelay);
    const jitter = Math.random() * this.jitterMax;
    const delay = exponentialDelay + jitter;

    setTimeout(() => {
      this.connect().then(() => {
        this.reconnectSuccessHandlers.forEach(handler => handler());
      }).catch(() => {
        // Reconnect failed, will try again if attempts remain
      });
    }, delay);
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
      // WebSocket is not connected. Cannot send message.
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

  offError(handler: (error: Event) => void): void {
    this.errorHandlers = this.errorHandlers.filter(h => h !== handler);
  }

  offClose(handler: (event: CloseEvent) => void): void {
    this.closeHandlers = this.closeHandlers.filter(h => h !== handler);
  }

  onReconnectFailed(handler: () => void): void {
    this.reconnectFailedHandlers.push(handler);
  }

  offReconnectFailed(handler: () => void): void {
    this.reconnectFailedHandlers = this.reconnectFailedHandlers.filter(h => h !== handler);
  }

  onReconnectSuccess(handler: () => void): void {
    this.reconnectSuccessHandlers.push(handler);
  }

  offReconnectSuccess(handler: () => void): void {
    this.reconnectSuccessHandlers = this.reconnectSuccessHandlers.filter(h => h !== handler);
  }

  isConnected(): boolean {

    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;

  }

  getReadyState(): number | undefined {

    return this.ws?.readyState;

  }

}
