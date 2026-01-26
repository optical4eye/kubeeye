// WebSocket client for connecting to backend WebSocket endpoint

import { WebSocketMessage, MessageType, PingMessage, PongMessage } from './messageTypes';

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
  private pingInterval: number | null = null;
  private pongTimeout: number | null = null;
  private pingIntervalMs = 30000; // 30 seconds
  private pongTimeoutMs = 10000; // 10 seconds

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
          console.log('WebSocket: Connection opened successfully, resetting reconnect attempts');
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
            } else if (message.type === 'pong') {
              this.handlePong();
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
            console.log(`WebSocket: Connection closed (code: ${event.code}), attempting reconnect`);
            this.attemptReconnect();
          } else {
            console.log(`WebSocket: Connection closed (code: ${event.code}), not reconnecting. Attempts: ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
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
    console.log(`WebSocket: Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

    // Exponential backoff with jitter
    const exponentialDelay = Math.min(this.baseDelay * Math.pow(2, this.reconnectAttempts - 1), this.maxDelay);
    const jitter = Math.random() * this.jitterMax;
    const delay = exponentialDelay + jitter;

    console.log(`WebSocket: Reconnect delay: ${delay.toFixed(0)}ms (exponential: ${exponentialDelay.toFixed(0)}ms, jitter: ${jitter.toFixed(0)}ms)`);

    setTimeout(() => {
      this.connect().then(() => {
        console.log('WebSocket: Reconnect successful');
      }).catch(() => {
        console.log('WebSocket: Reconnect failed, will try again if attempts remain');
      });
    }, delay);
  }

  disconnect(): void {
    this.stopPingPong();
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

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getReadyState(): number | undefined {
    return this.ws?.readyState;
  }

  private startPingPong(): void {
    this.stopPingPong(); // Ensure no existing intervals
    this.pingInterval = window.setInterval(() => {
      this.sendPing();
    }, this.pingIntervalMs);
  }

  private stopPingPong(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
  }

  private sendPing(): void {
    if (this.isConnected()) {
      const pingMessage: PingMessage = {
        type: 'ping',
        payload: {
          timestamp: new Date().toISOString(),
        },
        timestamp: new Date().toISOString(),
      };
      this.sendJson(pingMessage);
      // Set timeout for pong response
      this.pongTimeout = window.setTimeout(() => {
        console.warn('WebSocket: Pong timeout, closing connection');
        this.disconnect();
      }, this.pongTimeoutMs);
    }
  }

  private handlePong(): void {
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
  }
}
