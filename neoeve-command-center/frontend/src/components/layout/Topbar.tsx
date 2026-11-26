/**
 * Topbar - Application header with WebSocket indicator
 * Shows real connection state from Zustand store
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, useWebSocketStore } from '../../store';
import { apiClient } from '../../services/api';
import clsx from 'clsx';

export default function Topbar() {
  const navigate = useNavigate();
  // Use memoized selectors to prevent unnecessary re-renders
  const user = useAuthStore((state) => state.user);
  const resetAuth = useAuthStore((state) => state.reset);
  const isConnected = useWebSocketStore((state) => state.isConnected);

  const handleLogout = async () => {
    try {
      await apiClient.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      resetAuth();
      navigate('/login');
    }
  };

  return (
    <header
      role="banner"
      className="flex items-center justify-between border-b border-slate-800 bg-slate-800 px-6 py-4"
    >
      {/* Left side - Title */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-slate-50">
          NeoEve Command Center
        </h1>
      </div>

      {/* Right side - Status and User Info */}
      <div className="flex items-center gap-6">
        {/* WebSocket Indicator */}
        <div
          data-testid="ws-indicator"
          className="flex items-center gap-2"
        >
          <span
            className={clsx(
              'h-2 w-2 rounded-full transition-colors',
              isConnected
                ? 'bg-green-500'
                : 'bg-red-500'
            )}
          />
          <span className="text-xs text-slate-400">
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>

        {/* User Area */}
        {user && (
          <div
            data-testid="user-area"
            className="flex items-center gap-4 rounded-lg bg-slate-700 px-3 py-2"
          >
            <div className="flex flex-col text-sm">
              <span className="text-slate-50 font-medium">{user.actor_id}</span>
              <span className="text-xs text-slate-400">{user.actor_role}</span>
            </div>
            <button
              onClick={handleLogout}
              className="ml-2 rounded px-2 py-1 text-xs font-medium text-slate-50 hover:bg-slate-600 transition-colors"
            >
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
