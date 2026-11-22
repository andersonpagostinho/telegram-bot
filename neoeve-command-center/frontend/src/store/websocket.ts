/**
 * WebSocket Store
 * Manages real-time connection state and event subscriptions
 */

import { create } from 'zustand';
import { WebSocketState } from '../types/store';

export const useWebSocketStore = create<WebSocketState>((set) => ({
  isConnected: false,
  cursor: null,
  subscriptions: [],
  reconnectAttempts: 0,

  setConnected: (connected: boolean) =>
    set({ isConnected: connected }),

  setCursor: (cursor: number) =>
    set({ cursor }),

  subscribe: (eventTypes: string[]) =>
    set((state) => {
      const updated = new Set([...state.subscriptions, ...eventTypes]);
      return { subscriptions: Array.from(updated) };
    }),

  unsubscribe: (eventTypes: string[]) =>
    set((state) => {
      const toRemove = new Set(eventTypes);
      return {
        subscriptions: state.subscriptions.filter((s) => !toRemove.has(s)),
      };
    }),

  setReconnectAttempts: (attempts: number) =>
    set({ reconnectAttempts: attempts }),

  reset: () =>
    set({
      isConnected: false,
      cursor: null,
      subscriptions: [],
      reconnectAttempts: 0,
    }),
}));
