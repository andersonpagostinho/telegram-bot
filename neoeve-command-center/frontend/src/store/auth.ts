/**
 * Authentication Store
 * Manages user identity, tokens, and auth lifecycle
 */

import { create } from 'zustand';
import { AuthState, User } from '../types/store';

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  error: null,

  setAuth: (user: User, token: string) =>
    set({
      user,
      token,
      isLoading: false,
      error: null,
    }),

  setLoading: (loading: boolean) =>
    set({ isLoading: loading }),

  setError: (error: string | null) =>
    set({ error }),

  clearError: () =>
    set({ error: null }),

  reset: () =>
    set({
      user: null,
      token: null,
      isLoading: false,
      error: null,
    }),
}));
