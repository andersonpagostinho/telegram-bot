/**
 * UI Store
 * Manages transient UI state (preferences, notifications, etc.)
 */

import { create } from 'zustand';
import { UIState, UINotification } from '../types/store';

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  notifications: [],

  setSidebarOpen: (open: boolean) =>
    set({ sidebarOpen: open }),

  toggleSidebar: () =>
    set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setTheme: (theme: 'light' | 'dark') =>
    set({ theme }),

  addNotification: (message: string, type: UINotification['type']) =>
    set((state) => {
      const notification: UINotification = {
        id: `notif-${Date.now()}`,
        message,
        type,
        createdAt: Date.now(),
      };
      return { notifications: [...state.notifications, notification] };
    }),

  removeNotification: (id: string) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () =>
    set({ notifications: [] }),

  reset: () =>
    set({
      sidebarOpen: true,
      theme: 'dark',
      notifications: [],
    }),
}));
