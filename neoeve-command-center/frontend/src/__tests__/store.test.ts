import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../store/auth';
import { useWebSocketStore } from '../store/websocket';
import { useUIStore } from '../store/ui';

describe('Zustand Stores', () => {
  describe('Auth Store', () => {
    beforeEach(() => {
      useAuthStore.getState().reset();
    });

    it('should initialize with empty auth state', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should set user and token', () => {
      const store = useAuthStore.getState();
      store.setAuth({
        user_id: 'user-1',
        tenant_id: 'tenant-1',
        actor_id: 'actor-1',
        actor_role: 'architect',
      }, 'jwt-token-123');

      expect(store.user?.user_id).toBe('user-1');
      expect(store.token).toBe('jwt-token-123');
    });

    it('should track loading state', () => {
      const store = useAuthStore.getState();
      store.setLoading(true);
      expect(store.isLoading).toBe(true);

      store.setLoading(false);
      expect(store.isLoading).toBe(false);
    });

    it('should set and clear errors', () => {
      const store = useAuthStore.getState();
      store.setError('Authentication failed');
      expect(store.error).toBe('Authentication failed');

      store.clearError();
      expect(store.error).toBeNull();
    });

    it('should reset auth state', () => {
      const store = useAuthStore.getState();
      store.setAuth({
        user_id: 'user-1',
        tenant_id: 'tenant-1',
        actor_id: 'actor-1',
        actor_role: 'backend',
      }, 'token');

      store.reset();

      expect(store.user).toBeNull();
      expect(store.token).toBeNull();
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
    });

    it('should not expose credentials in logs', () => {
      const store = useAuthStore.getState();
      store.setAuth({
        user_id: 'user-1',
        tenant_id: 'tenant-1',
        actor_id: 'actor-1',
        actor_role: 'qa',
      }, 'secret-token');

      // Verify token is not in object properties that could be logged
      const stateStr = JSON.stringify(store);
      expect(stateStr).not.toContain('secret-token');
    });
  });

  describe('WebSocket Store', () => {
    beforeEach(() => {
      useWebSocketStore.getState().reset();
    });

    it('should initialize with disconnected state', () => {
      const state = useWebSocketStore.getState();
      expect(state.isConnected).toBe(false);
      expect(state.cursor).toBeNull();
      expect(state.subscriptions).toHaveLength(0);
    });

    it('should track connection state', () => {
      const store = useWebSocketStore.getState();
      store.setConnected(true);
      expect(store.isConnected).toBe(true);

      store.setConnected(false);
      expect(store.isConnected).toBe(false);
    });

    it('should update cursor from events', () => {
      const store = useWebSocketStore.getState();
      store.setCursor(42);
      expect(store.cursor).toBe(42);

      store.setCursor(100);
      expect(store.cursor).toBe(100);
    });

    it('should manage subscriptions', () => {
      const store = useWebSocketStore.getState();
      store.subscribe(['MISSION_UPDATED', 'EXECUTION_COMPLETED']);

      expect(store.subscriptions).toContain('MISSION_UPDATED');
      expect(store.subscriptions).toContain('EXECUTION_COMPLETED');
    });

    it('should not duplicate subscriptions', () => {
      const store = useWebSocketStore.getState();
      store.subscribe(['EVENT_A']);
      store.subscribe(['EVENT_A']);
      expect(store.subscriptions.length).toBe(1);
    });

    it('should track reconnection attempts', () => {
      const store = useWebSocketStore.getState();
      expect(store.reconnectAttempts).toBe(0);

      store.setReconnectAttempts(1);
      expect(store.reconnectAttempts).toBe(1);

      store.setReconnectAttempts(0);
      expect(store.reconnectAttempts).toBe(0);
    });

    it('should reset websocket state', () => {
      const store = useWebSocketStore.getState();
      store.setConnected(true);
      store.setCursor(50);
      store.subscribe(['EVENT_X']);

      store.reset();

      expect(store.isConnected).toBe(false);
      expect(store.cursor).toBeNull();
      expect(store.subscriptions).toHaveLength(0);
      expect(store.reconnectAttempts).toBe(0);
    });
  });

  describe('UI Store', () => {
    beforeEach(() => {
      useUIStore.getState().reset();
    });

    it('should initialize with default UI state', () => {
      const state = useUIStore.getState();
      expect(state.sidebarOpen).toBe(true);
      expect(state.theme).toBe('dark');
      expect(state.notifications).toHaveLength(0);
    });

    it('should toggle sidebar', () => {
      const store = useUIStore.getState();
      store.setSidebarOpen(false);
      expect(store.sidebarOpen).toBe(false);

      store.toggleSidebar();
      expect(store.sidebarOpen).toBe(true);
    });

    it('should change theme', () => {
      const store = useUIStore.getState();
      store.setTheme('light');
      expect(store.theme).toBe('light');

      store.setTheme('dark');
      expect(store.theme).toBe('dark');
    });

    it('should add notifications', () => {
      const store = useUIStore.getState();
      store.addNotification('Info message', 'info');

      expect(store.notifications).toHaveLength(1);
      expect(store.notifications[0].message).toBe('Info message');
      expect(store.notifications[0].type).toBe('info');
    });

    it('should remove notifications', () => {
      const store = useUIStore.getState();
      store.addNotification('Message 1', 'info');
      store.addNotification('Message 2', 'error');

      expect(store.notifications).toHaveLength(2);

      store.removeNotification(store.notifications[0].id);
      expect(store.notifications).toHaveLength(1);
    });

    it('should clear all notifications', () => {
      const store = useUIStore.getState();
      store.addNotification('Message 1', 'info');
      store.addNotification('Message 2', 'warning');

      store.clearNotifications();
      expect(store.notifications).toHaveLength(0);
    });

    it('should reset UI state', () => {
      const store = useUIStore.getState();
      store.setSidebarOpen(false);
      store.setTheme('light');
      store.addNotification('Test', 'info');

      store.reset();

      expect(store.sidebarOpen).toBe(true);
      expect(store.theme).toBe('dark');
      expect(store.notifications).toHaveLength(0);
    });
  });

  describe('Store Isolation', () => {
    it('should not duplicate data from API layer', () => {
      const authStore = useAuthStore.getState();
      const wsStore = useWebSocketStore.getState();

      // Auth store should only have auth info, not agent data
      expect(authStore).not.toHaveProperty('agents');
      expect(authStore).not.toHaveProperty('missions');

      // WebSocket store should only have connection state, not events
      expect(wsStore).not.toHaveProperty('events');
      expect(wsStore).not.toHaveProperty('agents');
    });

    it('should separate transient and persistent state', () => {
      const uiStore = useUIStore.getState();
      const wsStore = useWebSocketStore.getState();

      // UI store is transient (preferences)
      expect(uiStore.sidebarOpen).toBeDefined();
      expect(uiStore.theme).toBeDefined();

      // WebSocket store is session state (connection)
      expect(wsStore.isConnected).toBeDefined();
      expect(wsStore.cursor).toBeDefined();
    });
  });
});
