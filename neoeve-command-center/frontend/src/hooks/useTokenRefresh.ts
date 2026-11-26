/**
 * useTokenRefresh - Automatic token refresh before expiration
 * Renews access token 1 minute before 15-minute expiry
 * Shared refresh across concurrent requests
 */

import { useEffect, useRef } from 'react';
import { useAuthStore } from '../store/auth';
import { apiClient } from '../services/api';

let refreshPromise: Promise<boolean> | null = null;

export function useTokenRefresh() {
  const { token, setAuth, reset } = useAuthStore((state) => ({
    token: state.token,
    setAuth: state.setAuth,
    reset: state.reset,
  }));

  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!token) return;

    const scheduleRefresh = () => {
      // Clear any existing interval
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }

      // Schedule refresh every 14 minutes (1 min before 15-min expiry)
      refreshIntervalRef.current = setInterval(async () => {
        try {
          // Share refresh across concurrent requests
          if (!refreshPromise) {
            refreshPromise = performRefresh();
          }

          const success = await refreshPromise;
          refreshPromise = null;

          if (!success) {
            // Refresh failed - logout
            console.error('Token refresh failed, logging out');
            reset();
            window.location.href = '/login';
          }
        } catch (err) {
          console.error('Token refresh error:', err);
          refreshPromise = null;
          reset();
          window.location.href = '/login';
        }
      }, 14 * 60 * 1000); // 14 minutes
    };

    scheduleRefresh();

    // Also attempt an immediate refresh if token is very old
    // (happens when page is restored from background)
    performRefreshIfNeeded();

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [token, setAuth, reset]);

  return { token };
}

async function performRefresh(): Promise<boolean> {
  try {
    // Create a simple POST request via apiClient
    // Since refresh endpoint returns {access_token}, we extract from response
    const response = await (apiClient as any).client.post(
      '/auth/refresh',
      {}
    );

    if (!response.data?.access_token) {
      console.error('No access token in refresh response');
      return false;
    }

    // Update token in store
    apiClient.setToken(response.data.access_token);

    const authStore = useAuthStore.getState();
    const currentUser = authStore.user;

    if (currentUser) {
      authStore.setAuth(currentUser, response.data.access_token);
    }

    console.info('Token refreshed successfully');
    return true;
  } catch (err) {
    console.error('Token refresh request failed:', err);
    return false;
  }
}

async function performRefreshIfNeeded(): Promise<void> {
  // Check if we have a token and it might be close to expiry
  // This handles page restoration from background where interval might not have fired
  const authStore = useAuthStore.getState();

  if (!authStore.token) return;

  try {
    // Try a refresh - if it fails, it means token is invalid
    const response = await (apiClient as any).client.post(
      '/auth/refresh',
      {}
    );

    if (response.data?.access_token) {
      apiClient.setToken(response.data.access_token);
      authStore.setAuth(authStore.user!, response.data.access_token);
    }
  } catch (err) {
    // Silently fail - this is just an opportunistic refresh
    console.debug('Opportunistic refresh attempt failed (expected):', err);
  }
}
