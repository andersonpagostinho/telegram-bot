/**
 * WebSocket Service for real-time Command Center events
 * Implements ticket-based authentication, reconnection, and event recovery
 * With token renewal support (PHASE 2B integration)
 */

import { apiClient } from './api';
import { useAuthStore } from '../store/auth';

interface WebSocketTicketResponse {
  ticket: string;
}

interface WebSocketMessage {
  type?: string;
  event_id?: string;
  event_type?: string;
  event_types?: string[];
  data?: unknown;
  cursor?: number;
  timestamp?: string;
  code?: string;
  message?: string;
  action?: string;
}

interface WebSocketEventHandler {
  (event: { event_id: string; event_type: string; data: unknown }): void;
}

interface WebSocketErrorHandler {
  (error: { code: string; message: string }): void;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private ticket: string | null = null;
  private url: string;

  // Connection state
  public isConnected = false;
  public cursor: number | undefined = undefined;

  // Subscriptions
  public subscriptions: Set<string> = new Set();

  // Reconnection
  public maxRetries = 5;
  public initialRetryDelay = 1000;
  public maxRetryDelay = 30000;
  private retryCount = 0;
  private retryTimeout: ReturnType<typeof setTimeout> | null = null;
  private refreshAttempted = false; // Track if refresh was tried in this cycle

  // Event deduplication (sliding window)
  public recentEventIds: Map<string, number> = new Map();
  private deduplicationWindow = 300000; // 5 minutes

  // Event listeners
  private eventHandlers: Set<WebSocketEventHandler> = new Set();
  private errorHandlers: Set<WebSocketErrorHandler> = new Set();

  // Message queue
  public pendingMessages: WebSocketMessage[] = [];

  constructor() {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.url = baseUrl.replace('http', 'ws');
  }

  /**
   * Set authentication token (token is managed by API client, this is for integration)
   */
  public setToken(token: string): void {
    // Token is set on the API client via auth store
    // This method is here for hook compatibility
  }

  /**
   * Connect to WebSocket after obtaining ticket
   * Includes token renewal before requesting ticket (PHASE 2B integration)
   */
  async connect(): Promise<boolean> {
    try {
      this.refreshAttempted = false;

      // PHASE 2B: Ensure token is valid before requesting ticket
      const authStore = useAuthStore.getState();
      if (!authStore.token) {
        this.emitError('AUTH_ERROR', 'No authentication token available');
        return false;
      }

      // Try to get ticket
      return await this.requestTicketWithRetry();
    } catch (error: any) {
      this.emitError('CONNECTION_ERROR', error.message || 'Failed to connect');
      return false;
    }
  }

  /**
   * Request ticket with retry on 401 (attempt refresh once)
   */
  private async requestTicketWithRetry(): Promise<boolean> {
    try {
      const response = await apiClient.issueWebSocketTicket();
      this.ticket = (response as any).ticket;

      if (!this.ticket) {
        this.emitError('TICKET_ERROR', 'Failed to obtain WebSocket ticket');
        return false;
      }

      return this.establishConnection();
    } catch (error: any) {
      // If 401 and haven't tried refresh yet: attempt refresh + retry
      if (error.response?.status === 401 && !this.refreshAttempted) {
        this.refreshAttempted = true;
        console.info('Ticket request received 401, attempting token refresh...');

        // The interceptor in api.ts will handle refresh automatically
        // Just retry the ticket request once
        try {
          const response = await apiClient.issueWebSocketTicket();
          this.ticket = (response as any).ticket;

          if (!this.ticket) {
            this.emitError('TICKET_ERROR', 'Failed to obtain WebSocket ticket after refresh');
            return false;
          }

          console.info('Ticket obtained successfully after token refresh');
          return this.establishConnection();
        } catch (retryError: any) {
          this.emitError('AUTH_EXPIRED', 'Token refresh failed during ticket request');
          return false;
        }
      }

      // If 401 and already tried refresh: auth expired
      if (error.response?.status === 401) {
        this.emitError('AUTH_EXPIRED', 'Authentication expired');
        return false;
      }

      // Other errors
      this.emitError('TICKET_ERROR', error.message || 'Failed to obtain WebSocket ticket');
      return false;
    }
  }

  /**
   * Establish WebSocket connection with ticket
   */
  private establishConnection(): boolean {
    if (!this.ticket) {
      return false;
    }

    try {
      const wsUrl = `${this.url}/api/v1/websocket/ws?ticket=${encodeURIComponent(this.ticket)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => this.onOpen();
      this.ws.onmessage = (event) => this.onMessage(event);
      this.ws.onerror = (event) => this.onWSError(event);
      this.ws.onclose = () => this.onClose();

      return true;
    } catch (error: any) {
      this.emitError('CONNECTION_ERROR', error.message);
      return false;
    }
  }

  /**
   * Handle connection open
   */
  private onOpen(): void {
    this.isConnected = true;
    this.retryCount = 0;

    // Send initial subscription
    if (this.subscriptions.size > 0) {
      this.send({
        action: 'subscribe',
        event_types: Array.from(this.subscriptions),
      });
    }

    // If reconnecting, request missed events
    if (this.cursor !== undefined) {
      this.reconnect();
    }
  }

  /**
   * Handle incoming message
   */
  private onMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data) as WebSocketMessage;
      this.handleMessage(message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Process WebSocket message
   */
  public handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'event':
        this.handleEvent(message);
        break;
      case 'heartbeat':
        this.handleHeartbeat(message);
        break;
      case 'error':
        this.emitError(message.code || 'UNKNOWN_ERROR', message.message || 'Unknown error');
        break;
    }
  }

  /**
   * Handle event message with deduplication
   */
  private handleEvent(message: WebSocketMessage): void {
    const { event_id, event_type, data } = message;

    if (!event_id || !event_type) {
      console.warn('Invalid event message:', message);
      return;
    }

    // Check for duplicate
    if (this.recentEventIds.has(event_id)) {
      return;
    }

    // Track event for deduplication
    this.recentEventIds.set(event_id, Date.now());

    // Emit event to listeners
    this.eventHandlers.forEach((handler) => {
      handler({ event_id, event_type, data });
    });
  }

  /**
   * Handle heartbeat and cursor update
   */
  private handleHeartbeat(message: WebSocketMessage): void {
    if (message.cursor !== undefined) {
      this.cursor = message.cursor;
    }
  }

  /**
   * Handle WebSocket error
   */
  private onWSError(event: Event): void {
    console.error('WebSocket error:', event);
    this.emitError('WEBSOCKET_ERROR', 'Connection error');
  }

  /**
   * Handle connection closed
   */
  private onClose(): void {
    this.isConnected = false;
    this.ws = null;
    this.ticket = null; // Invalidate ticket (must get new one on reconnect)
    this.refreshAttempted = false; // Reset refresh flag for next attempt

    if (this.retryCount < this.maxRetries) {
      const delay = this.getRetryDelay(this.retryCount);
      this.retryTimeout = setTimeout(() => {
        this.retryCount++;
        this.connect();
      }, delay);
    } else {
      this.emitError('MAX_RETRIES_EXCEEDED', 'Failed to reconnect after maximum retries');
    }
  }

  /**
   * Subscribe to event types
   */
  subscribe(eventTypes: string[]): void {
    const before = this.subscriptions.size;
    eventTypes.forEach((type) => this.subscriptions.add(type));

    // If new subscriptions added and connected, send update
    if (this.subscriptions.size > before && this.isConnected) {
      this.send({
        action: 'subscribe',
        event_types: Array.from(this.subscriptions),
      });
    }
  }

  /**
   * Unsubscribe from event types
   */
  unsubscribe(eventTypes: string[]): void {
    eventTypes.forEach((type) => this.subscriptions.delete(type));
  }

  /**
   * Request missed events using cursor
   */
  public reconnect(): void {
    if (this.isConnected) {
      this.send({
        action: 'reconnect',
        cursor: this.cursor,
      });
    }
  }

  /**
   * Calculate exponential backoff delay
   */
  public getRetryDelay(retryCount: number): number {
    const delay = this.initialRetryDelay * Math.pow(2, retryCount);
    const jitter = Math.random() * 1000;
    return Math.min(delay + jitter, this.maxRetryDelay);
  }

  /**
   * Send message to server
   */
  private send(message: WebSocketMessage): void {
    if (this.isConnected && this.ws) {
      try {
        this.ws.send(JSON.stringify(message));
        this.pendingMessages.push(message);
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
      }
    }
  }

  /**
   * Register event listener
   */
  onEvent(handler: WebSocketEventHandler): () => void {
    this.eventHandlers.add(handler);
    return () => this.eventHandlers.delete(handler);
  }

  /**
   * Register error listener
   */
  onError(handler: WebSocketErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  /**
   * Emit error to handlers
   */
  private emitError(code: string, message: string): void {
    this.errorHandlers.forEach((handler) => {
      handler({ code, message });
    });
  }

  /**
   * Clean old entries from deduplication window
   */
  public cleanOldDuplicates(): void {
    const now = Date.now();
    const toDelete: string[] = [];

    this.recentEventIds.forEach((timestamp, eventId) => {
      if (now - timestamp > this.deduplicationWindow) {
        toDelete.push(eventId);
      }
    });

    toDelete.forEach((eventId) => this.recentEventIds.delete(eventId));
  }

  /**
   * Disconnect and cleanup
   */
  disconnect(): void {
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.cursor = undefined;
    this.ticket = null;
    this.eventHandlers.clear();
    this.errorHandlers.clear();
    this.pendingMessages = [];
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
