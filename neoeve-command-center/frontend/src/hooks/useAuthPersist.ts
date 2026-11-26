/**
 * useAuthPersist - Restore authentication from localStorage
 * Runs once on app initialization to restore session
 */

import { useEffect } from 'react';
import { useAuthStore } from '../store/auth';
import { apiClient } from '../services/api';

export function useAuthPersist() {
  const setAuth = useAuthStore((state) => state.setAuth);
  const reset = useAuthStore((state) => state.reset);

  useEffect(() => {
    // Try to restore token from localStorage
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');

    if (storedToken && storedUser) {
      try {
        const user = JSON.parse(storedUser);
        apiClient.setToken(storedToken);
        setAuth(user, storedToken);
      } catch (err) {
        console.error('Failed to restore auth from localStorage:', err);
        // Clear invalid data
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        reset();
      }
    }
  }, [setAuth, reset]);
}
