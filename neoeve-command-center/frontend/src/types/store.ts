/**
 * Zustand Store Type Definitions
 */

export interface User {
  user_id: string;
  tenant_id: string;
  actor_id: string;
  actor_role: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  setAuth: (user: User, token: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  reset: () => void;
}

export interface WebSocketState {
  isConnected: boolean;
  cursor: number | null;
  subscriptions: string[];
  reconnectAttempts: number;
  setConnected: (connected: boolean) => void;
  setCursor: (cursor: number) => void;
  subscribe: (eventTypes: string[]) => void;
  unsubscribe: (eventTypes: string[]) => void;
  setReconnectAttempts: (attempts: number) => void;
  reset: () => void;
}

export interface UINotification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  createdAt: number;
}

export interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  notifications: UINotification[];
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addNotification: (message: string, type: UINotification['type']) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  reset: () => void;
}
