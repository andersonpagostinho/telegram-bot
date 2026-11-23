import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { WebSocketService } from '../services/websocket';
import { apiClient } from '../services/api';

// Mock API client
vi.mock('../services/api', () => ({
  apiClient: {
    issueWebSocketTicket: vi.fn(),
  },
}));

describe('WebSocket Service', () => {
  let ws: WebSocketService;

  beforeEach(() => {
    ws = new WebSocketService();
    vi.clearAllMocks();
  });

  afterEach(() => {
    ws.disconnect();
  });

  describe('Initialization', () => {
    it('should create WebSocket service instance', () => {
      expect(ws).toBeDefined();
      expect(ws.isConnected).toBe(false);
      expect(ws.cursor).toBeNull();
    });

    it('should have reconnection configuration', () => {
      expect(ws.maxRetries).toBe(5);
      expect(ws.initialRetryDelay).toBe(1000);
      expect(ws.maxRetryDelay).toBe(30000);
    });
  });

  describe('Connection & Authentication', () => {
    it('should require ticket before connecting', async () => {
      const result = await ws.connect();
      expect(result).toBe(false);
    });

    it('should extract and store cursor from heartbeat', () => {
      const heartbeatMsg = {
        type: 'heartbeat',
        timestamp: new Date().toISOString(),
        cursor: 42,
      };

      ws.handleMessage(heartbeatMsg);
      expect(ws.cursor).toBe(42);
    });
  });

  describe('Subscriptions', () => {
    it('should track subscribed event types', () => {
      ws.subscribe(['MISSION_UPDATED', 'EXECUTION_COMPLETED']);
      expect(ws.subscriptions).toContain('MISSION_UPDATED');
      expect(ws.subscriptions).toContain('EXECUTION_COMPLETED');
    });

    it('should not duplicate subscriptions', () => {
      ws.subscribe(['EVENT_A']);
      ws.subscribe(['EVENT_A']);
      expect(ws.subscriptions.size).toBe(1);
    });
  });

  describe('Event Deduplication', () => {
    it('should deduplicate events by event_id', () => {
      const events: any[] = [];
      ws.onEvent((event) => events.push(event));

      ws.handleMessage({
        type: 'event',
        event_id: 'evt-123',
        event_type: 'MISSION_UPDATED',
        data: { mission_id: 'm1' },
      });

      ws.handleMessage({
        type: 'event',
        event_id: 'evt-123',  // Duplicate
        event_type: 'MISSION_UPDATED',
        data: { mission_id: 'm1' },
      });

      expect(events.length).toBe(1);
    });

    it('should track deduplication window', () => {
      const events: any[] = [];
      ws.onEvent((event) => events.push(event));

      ws.handleMessage({
        type: 'event',
        event_id: 'evt-456',
        event_type: 'EXECUTION_STARTED',
        data: { execution_id: 'e1' },
      });

      expect(events.length).toBe(1);
      expect(ws.recentEventIds.has('evt-456')).toBe(true);
    });
  });

  describe('Reconnection', () => {
    it('should calculate exponential backoff for retries', () => {
      const delays: number[] = [];
      for (let i = 0; i < 3; i++) {
        delays.push(ws.getRetryDelay(i));
      }

      // Should increase exponentially
      expect(delays[1]).toBeGreaterThan(delays[0]);
      expect(delays[2]).toBeGreaterThan(delays[1]);

      // Should not exceed maxRetryDelay
      expect(delays[2]).toBeLessThanOrEqual(ws.maxRetryDelay);
    });

    it('should send reconnect action with cursor', () => {
      ws.cursor = 42;
      const messages: any[] = [];
      ws.pendingMessages = messages;

      ws.reconnect();
      const msg = messages[messages.length - 1];

      expect(msg.action).toBe('reconnect');
      expect(msg.cursor).toBe(42);
    });
  });

  describe('Message Handlers', () => {
    it('should handle error messages', () => {
      let errorCaught: any;
      ws.onError((error) => { errorCaught = error; });

      ws.handleMessage({
        type: 'error',
        code: 'INVALID_TICKET',
        message: 'Ticket expired',
      });

      expect(errorCaught).toBeDefined();
      expect(errorCaught.code).toBe('INVALID_TICKET');
    });

    it('should validate event message structure', () => {
      const events: any[] = [];
      ws.onEvent((event) => events.push(event));

      ws.handleMessage({
        type: 'event',
        event_id: 'evt-789',
        event_type: 'MISSION_COMPLETED',
        data: { mission_id: 'm2' },
      });

      expect(events.length).toBe(1);
      expect(events[0].event_type).toBe('MISSION_COMPLETED');
    });
  });

  describe('Cleanup', () => {
    it('should clear resources on disconnect', () => {
      ws.cursor = 100;
      ws.disconnect();

      expect(ws.isConnected).toBe(false);
      expect(ws.cursor).toBeNull();
    });

    it('should clean old entries from deduplication window', () => {
      // Add event and immediately mark as old
      ws.recentEventIds.set('evt-old', Date.now() - 60000); // 60s old

      ws.cleanOldDuplicates();

      expect(ws.recentEventIds.has('evt-old')).toBe(false);
    });
  });
});
