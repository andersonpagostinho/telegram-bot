/**
 * useWebSocket - Integration with WebSocket service
 * Manages subscriptions, reconnection, and cache invalidation
 */

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { websocketService } from '../services/websocket';
import { useWebSocketStore, useAuthStore } from '../store';

interface WebSocketHookOptions {
  eventTypes?: string[];
}

export function useWebSocket({ eventTypes = [] }: WebSocketHookOptions = {}) {
  const queryClient = useQueryClient();
  // Use memoized selectors to prevent infinite re-renders
  // Without selectors, useWebSocketStore() returns a new object reference each time
  const isConnected = useWebSocketStore((state) => state.isConnected);
  const setConnected = useWebSocketStore((state) => state.setConnected);
  const setCursor = useWebSocketStore((state) => state.setCursor);
  const subscribe = useWebSocketStore((state) => state.subscribe);
  const { token } = useAuthStore();
  const connectionInitialized = useRef(false);

  // Initialize WebSocket connection once per token
  useEffect(() => {
    if (!token || connectionInitialized.current) return;

    connectionInitialized.current = true;
    websocketService.setToken(token);

    const connectWS = async () => {
      const success = await websocketService.connect();
      if (success) {
        setConnected(true);
      }
    };

    connectWS();

    // Subscribe to errors
    const unsubscribeError = websocketService.onError((error) => {
      console.error(`WebSocket error [${error.code}]: ${error.message}`, error);

      // Handle authentication expiration
      if (error.code === 'AUTH_EXPIRED' || error.code === 'UNAUTHORIZED') {
        setConnected(false);

        // Clear auth and logout on AUTH_EXPIRED
        if (error.code === 'AUTH_EXPIRED') {
          const authStore = useAuthStore.getState();
          authStore.reset();
          localStorage.removeItem('auth_token');
          localStorage.removeItem('auth_user');

          // Redirect to login (unless already there)
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
      }
    });

    return () => {
      unsubscribeError();
    };
  }, [token, setConnected]);

  // Subscribe to initial event types
  useEffect(() => {
    if (!isConnected || eventTypes.length === 0) return;

    websocketService.subscribe(eventTypes);
    subscribe(eventTypes);
  }, [isConnected, eventTypes, subscribe]);

  // Handle incoming events and invalidate cache
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeEvents = websocketService.onEvent((event) => {
      // Update cursor
      const cursorFromEvent = (event.data as any)?.cursor;
      if (cursorFromEvent) {
        setCursor(cursorFromEvent);
      }

      // Invalidate relevant cache based on event type
      switch (event.event_type) {
        case 'AGENT_UPDATED':
        case 'AGENT_STATUS_CHANGED':
          queryClient.invalidateQueries({ queryKey: ['agents'] });
          break;
        case 'MISSION_UPDATED':
        case 'MISSION_COMPLETED':
          queryClient.invalidateQueries({ queryKey: ['missions'] });
          break;
        case 'EXECUTION_STARTED':
        case 'EXECUTION_COMPLETED':
          queryClient.invalidateQueries({ queryKey: ['executions'] });
          break;
      }
    });

    return () => {
      unsubscribeEvents();
    };
  }, [isConnected, queryClient, setCursor]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Don't disconnect here - let other components keep the connection alive
      // but mark that we're done with this component
    };
  }, []);

  return {
    isConnected,
    connect: websocketService.connect,
    disconnect: websocketService.disconnect,
    onEvent: websocketService.onEvent.bind(websocketService),
  };
}
