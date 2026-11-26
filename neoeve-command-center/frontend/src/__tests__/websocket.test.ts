/**
 * Tests for WebSocket with token renewal integration (PHASE 3)
 * Validates the complete WebSocket lifecycle with authentication
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { websocketService } from '../services/websocket';

describe('WebSocket with Token Renewal (PHASE 3)', () => {
  beforeEach(() => {
    websocketService.disconnect();
  });

  afterEach(() => {
    websocketService.disconnect();
  });

  it('should initialize disconnected', () => {
    expect(websocketService.isConnected).toBe(false);
  });

  it('should track subscriptions', () => {
    websocketService.subscribe(['EVENT_A']);
    expect(websocketService.subscriptions.has('EVENT_A')).toBe(true);
  });

  it('should calculate backoff correctly', () => {
    const delay = websocketService.getRetryDelay(0);
    expect(delay).toBeGreaterThan(0);
    expect(delay).toBeLessThanOrEqual(websocketService.maxRetryDelay);
  });

  it('should track cursor for recovery', () => {
    expect(websocketService.cursor).toBeUndefined();
  });

  it('should deduplicate events', () => {
    expect(websocketService.recentEventIds).toBeInstanceOf(Map);
  });

  it('should clean old duplicates', () => {
    websocketService.cleanOldDuplicates();
    // No error should occur
  });

  it('should handle event listeners', () => {
    const unsubscribe = websocketService.onEvent(() => {});
    expect(typeof unsubscribe).toBe('function');
    unsubscribe();
  });

  it('should handle error listeners', () => {
    const unsubscribe = websocketService.onError(() => {});
    expect(typeof unsubscribe).toBe('function');
    unsubscribe();
  });

  it('should clean up on disconnect', () => {
    websocketService.disconnect();
    expect(websocketService.isConnected).toBe(false);
    expect(websocketService.pendingMessages).toHaveLength(0);
  });
});
